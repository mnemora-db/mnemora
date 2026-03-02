"""Health check endpoint handler.

Returns service status, version, and current timestamp.
This endpoint requires no authentication.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

VERSION = "0.1.0"


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle GET /v1/health requests.

    Args:
        event: API Gateway HTTP API event payload.
        context: Lambda execution context.

    Returns:
        API Gateway-compatible response with service health status.
    """
    start_time = time.time()
    request_id = _extract_request_id(event)

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": "/v1/health",
                "method": "GET",
            }
        )
    )

    latency_ms = round((time.time() - start_time) * 1000)

    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Request-Id",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": json.dumps(
            {
                "data": {
                    "status": "ok",
                    "version": VERSION,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                "meta": {
                    "request_id": request_id,
                    "latency_ms": latency_ms,
                },
            }
        ),
    }


def _extract_request_id(event: dict[str, Any]) -> str:
    """Extract request_id from API Gateway event context.

    Args:
        event: API Gateway HTTP API event payload.

    Returns:
        The request ID string, or 'unknown' if not found.
    """
    request_context = event.get("requestContext", {})
    return request_context.get("requestId", "unknown")
