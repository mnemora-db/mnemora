"""Aurora Serverless v2 warmer handler.

Invoked every 5 minutes by EventBridge to keep the Aurora cluster at a
responsive ACU level.  Uses a raw TCP socket to verify Aurora is reachable
(avoids psycopg3 async socket issues on Lambda) and warms the Secrets
Manager cache.

Environment variables:
    AURORA_HOST       – Cluster writer endpoint.
    AURORA_PORT       – PostgreSQL port (default: 5432).
    AURORA_SECRET_ARN – Secrets Manager ARN for DB credentials.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import time
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Keep Aurora warm by testing TCP connectivity and warming caches.

    Args:
        event: EventBridge scheduled event (ignored).
        context: Lambda execution context.

    Returns:
        Dict with status and latency.
    """
    start = time.time()
    host = os.environ.get("AURORA_HOST", "")
    port = int(os.environ.get("AURORA_PORT", "5432"))

    # Test TCP connectivity to Aurora
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    try:
        sock.connect((host, port))
        logger.info(f"Aurora TCP connection OK: {host}:{port}")
        sock.close()
    except Exception as e:
        latency_ms = round((time.time() - start) * 1000)
        logger.error(
            json.dumps(
                {
                    "action": "aurora_warm",
                    "status": "tcp_failed",
                    "error": str(e),
                    "latency_ms": latency_ms,
                }
            )
        )
        raise

    # Warm Secrets Manager cache
    import boto3  # noqa: PLC0415

    secret_arn = os.environ.get("AURORA_SECRET_ARN", "")
    if secret_arn:
        sm = boto3.client("secretsmanager")
        sm.get_secret_value(SecretId=secret_arn)
        logger.info("Secrets Manager cache warmed")

    latency_ms = round((time.time() - start) * 1000)
    logger.info(
        json.dumps(
            {
                "action": "aurora_warm",
                "status": "ok",
                "latency_ms": latency_ms,
            }
        )
    )
    return {"statusCode": 200, "body": "warm", "latency_ms": latency_ms}
