"""DynamoDB + S3 episode storage for Mnemora episodic memory.

Single-table design key structure::

    PK (pk)  = {tenant_id}#{agent_id}
    SK (sk)  = EPISODE#{ISO8601_timestamp}#{episode_id}

A GSI enables efficient session-scoped queries::

    gsi1pk = {tenant_id}#{session_id}
    gsi1sk = {ISO8601_timestamp}

Episodes have a 48-hour hot TTL in DynamoDB.  Older episodes can be
archived to S3 via :func:`archive_episode_to_s3`.

boto3 and botocore are imported lazily (inside functions) so that this
module can be imported in test environments where those packages are absent.
"""

from __future__ import annotations

import gzip
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HOT_TTL_HOURS = 48
_SESSION_GSI_NAME = "session-index"

# ---------------------------------------------------------------------------
# Module-level lazy resources — survive across warm Lambda invocations.
# ---------------------------------------------------------------------------

_table: Any | None = None
_s3_client: Any | None = None


def _get_table() -> Any:
    """Lazily initialise the DynamoDB Table resource.

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


def _get_s3_client() -> Any:
    """Lazily initialise the S3 client.

    Returns:
        boto3 S3 client instance.
    """
    global _s3_client
    if _s3_client is None:
        import boto3  # noqa: PLC0415

        _s3_client = boto3.client("s3")
    return _s3_client


# ---------------------------------------------------------------------------
# Key builders
# ---------------------------------------------------------------------------


def _build_pk(tenant_id: str, agent_id: str) -> str:
    """Construct the DynamoDB partition key for an agent."""
    return f"{tenant_id}#{agent_id}"


def _build_sk(timestamp: str, episode_id: str) -> str:
    """Construct the DynamoDB sort key for an episode item."""
    return f"EPISODE#{timestamp}#{episode_id}"


def _build_gsi1pk(tenant_id: str, session_id: str) -> str:
    """Construct the GSI session-index partition key."""
    return f"{tenant_id}#{session_id}"


# ---------------------------------------------------------------------------
# Sanitisation helpers
# ---------------------------------------------------------------------------


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


def _compute_ttl(hours: int = _HOT_TTL_HOURS) -> int:
    """Compute a Unix timestamp TTL *hours* from now.

    Args:
        hours: Number of hours until expiry.

    Returns:
        Unix timestamp integer.
    """
    return int(time.time()) + (hours * 3600)


# ---------------------------------------------------------------------------
# Item → response dict conversion
# ---------------------------------------------------------------------------


def _to_episode_dict(item: dict[str, Any]) -> dict[str, Any]:
    """Convert a raw DynamoDB episode item to a response dict.

    Extracts ``agent_id`` from ``pk`` (``{tenant_id}#{agent_id}``) and
    ``episode_id`` + ``timestamp`` from ``sk`` (``EPISODE#{ts}#{id}``).

    Args:
        item: Raw DynamoDB item dict returned by boto3.

    Returns:
        Dict matching the :class:`~lib.models.EpisodeResponse` shape.
    """
    pk: str = item.get("pk", "")
    pk_parts = pk.split("#", 1)
    agent_id = pk_parts[1] if len(pk_parts) > 1 else ""

    sk: str = item.get("sk", "")
    # SK format: EPISODE#<timestamp>#<episode_id>
    sk_no_prefix = sk.removeprefix("EPISODE#")
    sk_parts = sk_no_prefix.split("#", 1)
    timestamp = sk_parts[0] if sk_parts else ""
    episode_id = sk_parts[1] if len(sk_parts) > 1 else ""

    return {
        "id": episode_id,
        "agent_id": agent_id,
        "session_id": item.get("session_id", ""),
        "type": item.get("episode_type", ""),
        "content": item.get("content"),
        "metadata": item.get("metadata", {}),
        "timestamp": timestamp,
    }


# ---------------------------------------------------------------------------
# Public storage functions
# ---------------------------------------------------------------------------


def put_episode(
    tenant_id: str,
    agent_id: str,
    session_id: str,
    episode_type: str,
    content: Any,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Store a new episode in DynamoDB.

    Generates a UUID episode_id and an ISO 8601 timestamp.  Sets the TTL
    to 48 hours from now so that hot episodes are automatically expired.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.
        agent_id: Agent identifier.
        session_id: Session identifier used to group related episodes.
        episode_type: One of ``conversation``, ``action``, ``observation``,
            ``tool_call``.
        content: Episode payload — any JSON-serialisable value.
        metadata: Optional arbitrary JSON metadata.

    Returns:
        Dict matching the :class:`~lib.models.EpisodeResponse` shape.
    """
    episode_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    item: dict[str, Any] = {
        "pk": _build_pk(tenant_id, agent_id),
        "sk": _build_sk(timestamp, episode_id),
        # GSI attributes for session-scoped queries.
        "gsi1pk": _build_gsi1pk(tenant_id, session_id),
        "gsi1sk": timestamp,
        # Business fields.
        "session_id": session_id,
        "episode_type": episode_type,
        "content": _sanitise_for_dynamo(content),
        "metadata": _sanitise_for_dynamo(metadata or {}),
        "created_at": timestamp,
        "ttl": _compute_ttl(),
    }

    _get_table().put_item(Item=item)

    logger.info(
        json.dumps(
            {
                "action": "episode_put",
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "episode_type": episode_type,
            }
        )
    )

    return _to_episode_dict(item)


def query_episodes(
    tenant_id: str,
    agent_id: str,
    from_time: str | None = None,
    to_time: str | None = None,
    episode_type: str | None = None,
    session_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query episodes for an agent with optional filters.

    When ``session_id`` is provided the GSI ``session-index`` is used
    (``gsi1pk = {tenant_id}#{session_id}``).  Otherwise the main table is
    queried on ``pk = {tenant_id}#{agent_id}`` with ``sk BEGINS_WITH
    EPISODE#``.  Time-range filters apply a BETWEEN condition on the SK.
    An optional ``episode_type`` filter is applied via a DynamoDB
    FilterExpression.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.
        agent_id: Agent identifier.
        from_time: ISO 8601 lower bound for the episode timestamp (inclusive).
        to_time: ISO 8601 upper bound for the episode timestamp (inclusive).
        episode_type: Filter to a specific episode type.
        session_id: Restrict results to a single session via the GSI.
        limit: Maximum number of episodes to return (default 50).

    Returns:
        List of episode response dicts in chronological order.
    """
    import boto3.dynamodb.conditions as conditions  # noqa: PLC0415

    table = _get_table()

    if session_id is not None:
        # GSI path: query by session.
        gsi_pk = _build_gsi1pk(tenant_id, session_id)
        key_condition = conditions.Key("gsi1pk").eq(gsi_pk)

        if from_time and to_time:
            key_condition = key_condition & conditions.Key("gsi1sk").between(
                from_time, to_time
            )
        elif from_time:
            key_condition = key_condition & conditions.Key("gsi1sk").gte(from_time)
        elif to_time:
            key_condition = key_condition & conditions.Key("gsi1sk").lte(to_time)

        query_kwargs: dict[str, Any] = {
            "IndexName": _SESSION_GSI_NAME,
            "KeyConditionExpression": key_condition,
            "Limit": limit,
        }
    else:
        # Main table path: query by agent.
        pk = _build_pk(tenant_id, agent_id)

        if from_time and to_time:
            key_condition = conditions.Key("pk").eq(pk) & conditions.Key("sk").between(
                f"EPISODE#{from_time}",
                f"EPISODE#{to_time}\uffff",
            )
        elif from_time:
            key_condition = conditions.Key("pk").eq(pk) & conditions.Key("sk").between(
                f"EPISODE#{from_time}",
                "EPISODE#\uffff",
            )
        elif to_time:
            key_condition = conditions.Key("pk").eq(pk) & conditions.Key("sk").between(
                "EPISODE#",
                f"EPISODE#{to_time}\uffff",
            )
        else:
            key_condition = conditions.Key("pk").eq(pk) & conditions.Key(
                "sk"
            ).begins_with("EPISODE#")

        query_kwargs = {
            "KeyConditionExpression": key_condition,
            "Limit": limit,
        }

    if episode_type is not None:
        query_kwargs["FilterExpression"] = conditions.Attr("episode_type").eq(
            episode_type
        )

    response = table.query(**query_kwargs)
    items = response.get("Items", [])
    return [_to_episode_dict(item) for item in items]


def get_session_episodes(
    tenant_id: str,
    agent_id: str,
    session_id: str,
) -> list[dict[str, Any]]:
    """Get all episodes for a specific session, ordered by timestamp.

    Uses the GSI ``session-index`` keyed on
    ``gsi1pk = {tenant_id}#{session_id}`` with ``gsi1sk`` sorted by
    timestamp.  All episodes for the session are returned in chronological
    order.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.
        agent_id: Agent identifier (used for response mapping).
        session_id: Session identifier.

    Returns:
        List of episode response dicts in chronological order.
    """
    import boto3.dynamodb.conditions as conditions  # noqa: PLC0415

    gsi_pk = _build_gsi1pk(tenant_id, session_id)
    table = _get_table()
    results: list[dict[str, Any]] = []

    query_kwargs: dict[str, Any] = {
        "IndexName": _SESSION_GSI_NAME,
        "KeyConditionExpression": conditions.Key("gsi1pk").eq(gsi_pk),
        "ScanIndexForward": True,  # chronological order
    }

    while True:
        response = table.query(**query_kwargs)
        for item in response.get("Items", []):
            results.append(_to_episode_dict(item))

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        query_kwargs["ExclusiveStartKey"] = last_key

    return results


def get_recent_episodes(
    tenant_id: str,
    agent_id: str,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get the most recent N episodes for an agent.

    Queries ``pk = {tenant_id}#{agent_id}`` with ``sk BEGINS_WITH
    EPISODE#`` in reverse chronological order (``ScanIndexForward=False``),
    then reverses the result list so the caller receives episodes in
    chronological order.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.
        agent_id: Agent identifier.
        limit: Maximum number of episodes to return (default 50).

    Returns:
        List of episode response dicts in chronological order (oldest first).
    """
    import boto3.dynamodb.conditions as conditions  # noqa: PLC0415

    pk = _build_pk(tenant_id, agent_id)
    table = _get_table()

    response = table.query(
        KeyConditionExpression=(
            conditions.Key("pk").eq(pk) & conditions.Key("sk").begins_with("EPISODE#")
        ),
        ScanIndexForward=False,
        Limit=limit,
    )

    items = response.get("Items", [])
    # Reverse so we return oldest-first chronological order.
    return [_to_episode_dict(item) for item in reversed(items)]


def archive_episode_to_s3(
    tenant_id: str,
    agent_id: str,
    episode: dict[str, Any],
) -> str:
    """Archive a single episode to S3 cold storage.

    Compresses the episode JSON with gzip and uploads to::

        s3://{bucket}/{tenant_id}/{agent_id}/{date}/{episode_id}.json.gz

    Args:
        tenant_id: Tenant identifier (used as S3 key prefix).
        agent_id: Agent identifier (second path component).
        episode: Episode dict as returned by :func:`put_episode` or
            :func:`_to_episode_dict`.

    Returns:
        The S3 key for the uploaded object.

    Raises:
        botocore.exceptions.ClientError: On any S3 API error.
    """
    bucket = os.environ.get("EPISODE_BUCKET_NAME", "")

    episode_id = episode.get("id", str(uuid.uuid4()))
    timestamp = episode.get("timestamp", datetime.now(timezone.utc).isoformat())
    # Parse the date portion for the S3 path prefix.
    try:
        date_str = timestamp[:10]  # "YYYY-MM-DD"
    except (TypeError, IndexError):
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    s3_key = f"{tenant_id}/{agent_id}/{date_str}/{episode_id}.json.gz"

    compressed = gzip.compress(json.dumps(episode).encode("utf-8"))

    _get_s3_client().put_object(
        Bucket=bucket,
        Key=s3_key,
        Body=compressed,
        ContentType="application/json",
        ContentEncoding="gzip",
    )

    logger.info(
        json.dumps(
            {
                "action": "episode_archived",
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "s3_key": s3_key,
            }
        )
    )

    return s3_key
