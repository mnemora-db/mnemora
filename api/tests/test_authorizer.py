"""Tests for api/handlers/auth.py — API key authorizer."""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock

# Ensure test env vars are set before importing the handler.
os.environ.setdefault("MNEMORA_TEST_API_KEY", "test-key-for-unit-tests")
os.environ.setdefault("MNEMORA_TEST_TENANT", "test-tenant")

from handlers.auth import handler  # noqa: E402

# Use the env-configured test key
VALID_TEST_KEY = os.environ["MNEMORA_TEST_API_KEY"]


class TestAuthorizerValidKey:
    """Tests for valid API key authorization."""

    def test_auth_accepts_valid_bearer_key(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange
        event = mock_event_factory(
            headers={"authorization": f"Bearer {VALID_TEST_KEY}"}
        )

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is True

    def test_auth_returns_tenant_id_in_context(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange
        event = mock_event_factory(
            headers={"authorization": f"Bearer {VALID_TEST_KEY}"}
        )

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["context"]["tenantId"] == "test-tenant"

    def test_auth_accepts_raw_key_without_bearer_prefix(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange — send key without "Bearer " prefix
        event = mock_event_factory(headers={"authorization": VALID_TEST_KEY})

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is True
        assert result["context"]["tenantId"] == "test-tenant"


class TestAuthorizerMissingKey:
    """Tests for missing API key."""

    def test_auth_rejects_missing_key(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange — no authorization header
        event = mock_event_factory(headers={"authorization": ""})

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is False

    def test_auth_rejects_empty_headers(self, mock_context: MagicMock) -> None:
        # Arrange — event with no headers at all
        event: dict[str, Any] = {
            "headers": {},
            "requestContext": {"requestId": "test-id", "http": {"method": "GET"}},
            "rawPath": "/v1/state",
        }

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is False
        assert result["context"] == {}

    def test_auth_rejects_missing_headers_key(self, mock_context: MagicMock) -> None:
        # Arrange — event without headers dict
        event: dict[str, Any] = {
            "requestContext": {"requestId": "test-id", "http": {"method": "GET"}},
            "rawPath": "/v1/state",
        }

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is False


class TestAuthorizerInvalidKey:
    """Tests for invalid API keys."""

    def test_auth_rejects_invalid_key(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange
        event = mock_event_factory(
            headers={"authorization": "Bearer totally-wrong-key"}
        )

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is False
        assert result["context"] == {}

    def test_auth_rejects_partial_key(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange — partial match of the valid key
        event = mock_event_factory(headers={"authorization": "Bearer partial-wrong-key"})

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is False

    def test_auth_rejects_whitespace_only_key(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange
        event = mock_event_factory(headers={"authorization": "Bearer    "})

        # Act
        result = handler(event, mock_context)

        # Assert
        assert result["isAuthorized"] is False

    def test_auth_deny_response_has_correct_structure(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        # Arrange
        event = mock_event_factory(headers={"authorization": "Bearer bad-key"})

        # Act
        result = handler(event, mock_context)

        # Assert
        assert "isAuthorized" in result
        assert "context" in result
        assert result["isAuthorized"] is False
        assert isinstance(result["context"], dict)
