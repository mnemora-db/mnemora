"""API key authorizer handler for HTTP API Gateway.

Validates the API key from the Authorization header and returns a
SimpleAuthorizerResult with tenant_id context. API keys are loaded
from environment variables at module init. Production deployments
should use DynamoDB lookup (PK=APIKEY#<hash>, SK=META).

SECURITY: Never log API keys or full authorization headers.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# API key → tenant mapping.
# Load test keys from environment. Format: "key1:tenant1,key2:tenant2"
# Falls back to the MNEMORA_TEST_API_KEY env var for single-key dev setups.
_TEST_KEYS: dict[str, str] = {}


def _load_api_keys() -> dict[str, str]:
    """Load API key → tenant mappings from environment variables.

    Supports two env vars:
    - MNEMORA_API_KEYS: Comma-separated "key:tenant" pairs.
    - MNEMORA_TEST_API_KEY + MNEMORA_TEST_TENANT: Single key for development.

    Returns:
        Dict mapping SHA-256 key hashes to tenant IDs.
    """
    keys: dict[str, str] = {}

    # Multi-key format: "key1:tenant1,key2:tenant2"
    api_keys_env = os.environ.get("MNEMORA_API_KEYS", "")
    if api_keys_env:
        for pair in api_keys_env.split(","):
            pair = pair.strip()
            if ":" in pair:
                raw_key, tenant = pair.split(":", 1)
                key_hash = hashlib.sha256(raw_key.strip().encode()).hexdigest()
                keys[key_hash] = tenant.strip()

    # Single-key dev shortcut
    test_key = os.environ.get("MNEMORA_TEST_API_KEY", "")
    test_tenant = os.environ.get("MNEMORA_TEST_TENANT", "dev-tenant")
    if test_key:
        key_hash = hashlib.sha256(test_key.encode()).hexdigest()
        keys[key_hash] = test_tenant

    return keys


# Load once at module init (Lambda cold start).
_TEST_KEYS = _load_api_keys()


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle Lambda authorizer requests for HTTP API Gateway.

    Expects Simple response format (HTTP API v2 payload).

    Args:
        event: Authorizer event with headers and requestContext.
        context: Lambda execution context.

    Returns:
        SimpleAuthorizerResult: {"isAuthorized": bool, "context": {...}}.
    """
    start_time = time.time()
    request_id = event.get("requestContext", {}).get("requestId", "unknown")

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": event.get("rawPath", "unknown"),
                "method": event.get("requestContext", {})
                .get("http", {})
                .get("method", "unknown"),
                "action": "authorize",
            }
        )
    )

    api_key = _extract_api_key(event)

    if not api_key:
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "action": "authorize",
                    "result": "denied",
                    "reason": "missing_key",
                    "latency_ms": round((time.time() - start_time) * 1000),
                }
            )
        )
        return _deny_response()

    tenant_id = _resolve_tenant(api_key)

    if not tenant_id:
        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "action": "authorize",
                    "result": "denied",
                    "reason": "invalid_key",
                    "latency_ms": round((time.time() - start_time) * 1000),
                }
            )
        )
        return _deny_response()

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "action": "authorize",
                "result": "allowed",
                "tenant_id": tenant_id,
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return {
        "isAuthorized": True,
        "context": {
            "tenantId": tenant_id,
        },
    }


def _extract_api_key(event: dict[str, Any]) -> str | None:
    """Extract API key from the Authorization header.

    Supports formats:
    - "Bearer <key>"
    - "<key>" (raw)

    Args:
        event: API Gateway authorizer event.

    Returns:
        The raw API key string, or None if not present.
    """
    headers = event.get("headers", {})
    auth_header = headers.get("authorization", "")

    if not auth_header:
        return None

    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return auth_header.strip() or None


def _resolve_tenant(api_key: str) -> str | None:
    """Resolve an API key to a tenant_id.

    MVP: Checks against hardcoded test keys (SHA-256 hash comparison).
    Production: DynamoDB lookup on PK=APIKEY#<sha256_hash>, SK=META.

    Args:
        api_key: Raw API key string.

    Returns:
        tenant_id if the key is valid, None otherwise.
    """
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    return _TEST_KEYS.get(key_hash)


def _deny_response() -> dict[str, Any]:
    """Build a deny response for the authorizer.

    Returns:
        SimpleAuthorizerResult denying access.
    """
    return {
        "isAuthorized": False,
        "context": {},
    }
