"""DynamoDB client wrapper for Mnemora working memory.

Single-table design with the following key structure:
    PK = {tenant_id}#{agent_id}
    SK = SESSION#{session_id}

Every item carries: created_at, updated_at, ttl (Unix timestamp), version.

boto3 and botocore are imported lazily (inside functions) so that this
module can be imported in test environments where those packages are absent.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_TTL_HOURS = 24
_table = None


def _get_table() -> Any:
    """Lazy-initialise the DynamoDB Table resource.

    Returns:
        boto3 DynamoDB Table resource bound to STATE_TABLE_NAME.
    """
    global _table
    if _table is None:
        import boto3  # noqa: PLC0415

        table_name = os.environ.get("STATE_TABLE_NAME", "mnemora-state-dev")
        dynamodb = boto3.resource("dynamodb")
        _table = dynamodb.Table(table_name)
    return _table


def _build_pk(tenant_id: str, agent_id: str) -> str:
    """Construct the DynamoDB partition key."""
    return f"{tenant_id}#{agent_id}"


def _build_sk(session_id: str) -> str:
    """Construct the DynamoDB sort key for a session item."""
    return f"SESSION#{session_id}"


def _sanitise_for_dynamo(data: Any) -> Any:
    """Recursively convert Python floats to ``Decimal`` for DynamoDB.

    The boto3 DynamoDB Table resource rejects native ``float`` values and
    requires ``decimal.Decimal`` instead.  This helper round-trips through
    JSON (which normalises nested structures) and re-parses floats as
    ``Decimal``.

    Args:
        data: Arbitrary JSON-compatible value (dict, list, scalar).

    Returns:
        Same structure with all floats replaced by Decimal.
    """
    return json.loads(json.dumps(data), parse_float=Decimal)


def _compute_ttl(ttl_hours: int | None) -> int:
    """Compute the Unix timestamp for TTL expiry.

    Args:
        ttl_hours: Hours until expiry. Uses _DEFAULT_TTL_HOURS when None.

    Returns:
        Unix timestamp integer.
    """
    hours = ttl_hours if ttl_hours is not None else _DEFAULT_TTL_HOURS
    return int(time.time()) + (hours * 3600)


def _to_state_dict(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a raw DynamoDB item to a clean state response dict.

    Strips internal DynamoDB keys (pk, sk) and converts the ttl Unix
    timestamp to an ISO 8601 string in expires_at.  Numeric values
    (version, ttl) are explicitly cast to ``int`` because DynamoDB's
    boto3 resource returns them as ``decimal.Decimal``, which is not
    JSON-serialisable.

    Args:
        item: Raw DynamoDB item dict.

    Returns:
        Clean state dict suitable for API responses.
    """
    pk = item.get("pk", "")
    parts = pk.split("#", 1)
    agent_id = parts[1] if len(parts) > 1 else ""

    sk = item.get("sk", "")
    session_id = sk.removeprefix("SESSION#")

    expires_at: str | None = None
    raw_ttl = item.get("ttl")
    if raw_ttl:
        expires_at = datetime.fromtimestamp(int(raw_ttl), tz=timezone.utc).isoformat()

    return {
        "agent_id": agent_id,
        "session_id": session_id,
        "data": item.get("data", {}),
        "version": int(item.get("version", 1)),
        "created_at": item.get("created_at", ""),
        "updated_at": item.get("updated_at", ""),
        "expires_at": expires_at,
    }


def put_state(
    tenant_id: str,
    agent_id: str,
    session_id: str,
    data: dict[str, Any],
    ttl_hours: int | None = None,
) -> dict[str, Any]:
    """Create a new state item in DynamoDB (version starts at 1).

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.
        agent_id: Agent identifier.
        session_id: Session identifier.
        data: Arbitrary JSON-serialisable state payload.
        ttl_hours: Optional TTL override in hours.

    Returns:
        Clean state dict matching StateResponse shape.
    """
    now = datetime.now(timezone.utc).isoformat()
    item: dict[str, Any] = {
        "pk": _build_pk(tenant_id, agent_id),
        "sk": _build_sk(session_id),
        "data": _sanitise_for_dynamo(data),
        "version": 1,
        "created_at": now,
        "updated_at": now,
        "ttl": _compute_ttl(ttl_hours),
    }
    _get_table().put_item(Item=item)
    return _to_state_dict(item)


def get_state(tenant_id: str, agent_id: str, session_id: str) -> dict[str, Any] | None:
    """Fetch a single state item.

    Args:
        tenant_id: Tenant identifier.
        agent_id: Agent identifier.
        session_id: Session identifier.

    Returns:
        Clean state dict, or None if the item does not exist.
    """
    response = _get_table().get_item(
        Key={
            "pk": _build_pk(tenant_id, agent_id),
            "sk": _build_sk(session_id),
        }
    )
    item = response.get("Item")
    if not item:
        return None
    return _to_state_dict(item)


def list_sessions(tenant_id: str, agent_id: str) -> list[dict[str, Any]]:
    """List all sessions for an agent, handling DynamoDB pagination.

    Args:
        tenant_id: Tenant identifier.
        agent_id: Agent identifier.

    Returns:
        List of clean state dicts, one per session.
    """
    import boto3.dynamodb.conditions  # noqa: PLC0415

    pk = _build_pk(tenant_id, agent_id)
    results: list[dict[str, Any]] = []

    kwargs: dict[str, Any] = {
        "KeyConditionExpression": (
            boto3.dynamodb.conditions.Key("pk").eq(pk)
            & boto3.dynamodb.conditions.Key("sk").begins_with("SESSION#")
        ),
    }

    while True:
        response = _get_table().query(**kwargs)
        for item in response.get("Items", []):
            results.append(_to_state_dict(item))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    return results


def update_state(
    tenant_id: str,
    agent_id: str,
    session_id: str,
    data: dict[str, Any],
    expected_version: int,
    ttl_hours: int | None = None,
) -> dict[str, Any]:
    """Update state with optimistic locking via a version condition.

    Args:
        tenant_id: Tenant identifier.
        agent_id: Agent identifier.
        session_id: Session identifier.
        data: New state payload to write.
        expected_version: The caller's current version; incremented on success.
        ttl_hours: Optional TTL override in hours.

    Returns:
        Clean state dict reflecting the newly written item.

    Raises:
        ClientError: Re-raised for any DynamoDB error, including
            ConditionalCheckFailedException on version mismatch.
    """
    now = datetime.now(timezone.utc).isoformat()

    update_expr = "SET #data = :data, #version = :new_version, #updated_at = :now"
    expr_names: dict[str, str] = {
        "#data": "data",
        "#version": "version",
        "#updated_at": "updated_at",
    }
    expr_values: dict[str, Any] = {
        ":data": _sanitise_for_dynamo(data),
        ":new_version": expected_version + 1,
        ":now": now,
        ":expected_version": expected_version,
    }

    if ttl_hours is not None:
        update_expr += ", #ttl = :ttl"
        expr_names["#ttl"] = "ttl"
        expr_values[":ttl"] = _compute_ttl(ttl_hours)

    response = _get_table().update_item(
        Key={
            "pk": _build_pk(tenant_id, agent_id),
            "sk": _build_sk(session_id),
        },
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
        ConditionExpression="attribute_exists(pk) AND #version = :expected_version",
        ReturnValues="ALL_NEW",
    )
    return _to_state_dict(response["Attributes"])


def delete_state(tenant_id: str, agent_id: str, session_id: str) -> bool:
    """Delete a state item.

    Uses a condition expression so the call is idempotent-safe — it returns
    False rather than raising when the item does not exist.

    Args:
        tenant_id: Tenant identifier.
        agent_id: Agent identifier.
        session_id: Session identifier.

    Returns:
        True if the item existed and was deleted, False if it was not found.

    Raises:
        ClientError: Re-raised for any DynamoDB error other than
            ConditionalCheckFailedException.
    """
    from botocore.exceptions import ClientError  # noqa: PLC0415

    try:
        _get_table().delete_item(
            Key={
                "pk": _build_pk(tenant_id, agent_id),
                "sk": _build_sk(session_id),
            },
            ConditionExpression="attribute_exists(pk)",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise
