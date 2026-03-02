"""Shared test fixtures for Mnemora API handler tests.

Provides mock API Gateway v2 events and Lambda context objects
that mirror the real HTTP API payload format.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock

import pytest

# Set test API key env vars BEFORE any handler imports.
# This ensures the auth module loads the test key at module init.
os.environ.setdefault("MNEMORA_TEST_API_KEY", "test-key-for-unit-tests")
os.environ.setdefault("MNEMORA_TEST_TENANT", "test-tenant")

# Constant for use in test assertions and mock events.
TEST_API_KEY = os.environ["MNEMORA_TEST_API_KEY"]
TEST_TENANT = os.environ["MNEMORA_TEST_TENANT"]


@pytest.fixture()
def mock_context() -> MagicMock:
    """Create a mock Lambda execution context.

    Returns:
        MagicMock with standard Lambda context attributes.
    """
    ctx = MagicMock()
    ctx.function_name = "mnemora-test"
    ctx.memory_limit_in_mb = 256
    ctx.invoked_function_arn = (
        "arn:aws:lambda:us-east-1:123456789012:function:mnemora-test"
    )
    ctx.aws_request_id = "test-lambda-request-id"
    return ctx


@pytest.fixture()
def mock_event() -> dict[str, Any]:
    """Create a mock API Gateway HTTP API v2 event.

    Returns:
        Dict matching the API Gateway v2 payload format with
        requestContext, headers, and authorizer context.
    """
    return {
        "version": "2.0",
        "routeKey": "GET /v1/health",
        "rawPath": "/v1/health",
        "rawQueryString": "",
        "headers": {
            "content-type": "application/json",
            "authorization": f"Bearer {TEST_API_KEY}",
        },
        "requestContext": {
            "requestId": "test-request-id-12345",
            "http": {
                "method": "GET",
                "path": "/v1/health",
                "sourceIp": "127.0.0.1",
            },
            "authorizer": {
                "lambda": {
                    "tenantId": "test-tenant",
                },
            },
        },
        "body": None,
        "isBase64Encoded": False,
    }


@pytest.fixture()
def mock_event_factory() -> Any:
    """Factory fixture for creating custom API Gateway v2 events.

    Returns:
        Callable that accepts overrides and returns a complete event dict.
    """

    def _make_event(
        method: str = "GET",
        path: str = "/v1/health",
        headers: dict[str, str] | None = None,
        body: str | None = None,
        tenant_id: str = "test-tenant",
        request_id: str = "test-request-id-12345",
    ) -> dict[str, Any]:
        """Build a mock API Gateway HTTP API v2 event.

        Args:
            method: HTTP method.
            path: Request path.
            headers: HTTP headers (merged with defaults).
            body: Request body string.
            tenant_id: Tenant ID in authorizer context.
            request_id: Request ID in requestContext.

        Returns:
            Complete API Gateway v2 event dict.
        """
        default_headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {TEST_API_KEY}",
        }
        if headers:
            default_headers.update(headers)

        return {
            "version": "2.0",
            "routeKey": f"{method} {path}",
            "rawPath": path,
            "rawQueryString": "",
            "headers": default_headers,
            "requestContext": {
                "requestId": request_id,
                "http": {
                    "method": method,
                    "path": path,
                    "sourceIp": "127.0.0.1",
                },
                "authorizer": {
                    "lambda": {
                        "tenantId": tenant_id,
                    },
                },
            },
            "body": body,
            "isBase64Encoded": False,
        }

    return _make_event
