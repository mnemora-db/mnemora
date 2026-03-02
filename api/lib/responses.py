"""Standardized API response utilities for Lambda handlers.

All API responses follow the format defined in CLAUDE.md:
- Success: {"data": ..., "meta": {"request_id": "...", "latency_ms": N}}
- Error: {"error": {"code": "...", "message": "..."}, "meta": {...}}
"""

from __future__ import annotations

import json
import time
from decimal import Decimal
from typing import Any


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that converts ``decimal.Decimal`` to ``int`` or ``float``.

    DynamoDB's boto3 Table resource returns all numeric values as
    ``decimal.Decimal``.  The standard ``json.dumps`` cannot serialise
    them, so we provide this thin encoder as a safety net.
    """

    def default(self, o: Any) -> Any:  # noqa: ANN401
        if isinstance(o, Decimal):
            return int(o) if o == int(o) else float(o)
        return super().default(o)


CORS_HEADERS: dict[str, str] = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Request-Id",
    "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
}


def success_response(
    body: Any,
    status: int = 200,
    request_id: str = "",
    start_time: float | None = None,
) -> dict[str, Any]:
    """Build a standardized success response for API Gateway.

    Args:
        body: The response data payload.
        status: HTTP status code (default 200).
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp from request start for latency calculation.

    Returns:
        API Gateway-compatible response dict with CORS headers.
    """
    latency_ms = round((time.time() - start_time) * 1000) if start_time else 0

    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(
            {
                "data": body,
                "meta": {
                    "request_id": request_id,
                    "latency_ms": latency_ms,
                },
            },
            cls=_DecimalEncoder,
        ),
    }


def error_response(
    message: str,
    status: int = 500,
    error_code: str = "INTERNAL_ERROR",
    request_id: str = "",
) -> dict[str, Any]:
    """Build a standardized error response for API Gateway.

    Args:
        message: Human-readable error description.
        status: HTTP status code (default 500).
        error_code: Machine-readable error code (e.g. VALIDATION_ERROR).
        request_id: Unique request identifier for tracing.

    Returns:
        API Gateway-compatible error response dict with CORS headers.
    """
    return {
        "statusCode": status,
        "headers": CORS_HEADERS,
        "body": json.dumps(
            {
                "error": {
                    "code": error_code,
                    "message": message,
                },
                "meta": {
                    "request_id": request_id,
                },
            },
            cls=_DecimalEncoder,
        ),
    }
