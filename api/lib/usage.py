"""DynamoDB-based usage tracking for Mnemora.

Tracks per-tenant API usage counters with atomic increments using
DynamoDB's UpdateExpression ADD operator, which is safe for concurrent
Lambda invocations.

Key structure::

    PK = {tenant_id}#USAGE
    SK = MONTH#{YYYY-MM}

Counters stored per item:
    api_calls       — total API calls in the month
    embeddings      — embedding generations in the month
    storage_bytes   — approximate storage in bytes (informational)

boto3 is imported lazily (inside functions) so this module can be imported
in test environments where boto3 is absent.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_table: Any | None = None


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


def _current_month_sk() -> str:
    """Return the sort key for the current calendar month.

    Returns:
        String in the format ``MONTH#YYYY-MM``.
    """
    now = datetime.now(timezone.utc)
    return f"MONTH#{now.strftime('%Y-%m')}"


def _build_pk(tenant_id: str) -> str:
    """Construct the DynamoDB partition key for usage tracking.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.

    Returns:
        Partition key string.
    """
    return f"{tenant_id}#USAGE"


def increment_counter(
    tenant_id: str,
    counter_name: str,
    amount: int = 1,
) -> None:
    """Atomically increment a usage counter for the current month.

    Uses DynamoDB's ``ADD`` UpdateExpression which is safe for concurrent
    Lambda invocations — no read-modify-write race conditions.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.
        counter_name: Name of the counter attribute to increment (e.g.
            ``"api_calls"``, ``"embeddings"``).
        amount: Amount to add (default 1).
    """
    table = _get_table()
    pk = _build_pk(tenant_id)
    sk = _current_month_sk()

    table.update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression="ADD #counter :amount",
        ExpressionAttributeNames={"#counter": counter_name},
        ExpressionAttributeValues={":amount": amount},
    )

    logger.info(
        "Usage counter incremented",
        extra={
            "tenant_id": tenant_id,
            "counter": counter_name,
            "amount": amount,
        },
    )


def get_usage(tenant_id: str) -> dict[str, Any]:
    """Retrieve current month usage stats for a tenant from DynamoDB.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.

    Returns:
        Dict with usage counters. Missing counters default to 0.
    """
    table = _get_table()
    pk = _build_pk(tenant_id)
    sk = _current_month_sk()

    response = table.get_item(Key={"pk": pk, "sk": sk})
    item = response.get("Item", {})

    return {
        "api_calls": int(item.get("api_calls", 0)),
        "embeddings": int(item.get("embeddings", 0)),
        "storage_bytes": int(item.get("storage_bytes", 0)),
        "month": sk.removeprefix("MONTH#"),
    }
