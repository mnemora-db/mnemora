"""Tests for api/handlers/auth.py — API key authorizer."""

from __future__ import annotations

import hashlib
import os
from typing import Any
from unittest.mock import MagicMock, patch

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
        event = mock_event_factory(
            headers={"authorization": "Bearer partial-wrong-key"}
        )

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


class TestAuthorizerDynamoDBLookup:
    """Tests for DynamoDB-backed API key lookup."""

    def test_dynamo_lookup_finds_valid_key(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        """Key not in env vars but present in DynamoDB should be authorized."""
        import handlers.auth as auth_mod

        dynamo_key = "mnm_dynamo_test_key_abc123"
        key_hash = hashlib.sha256(dynamo_key.encode()).hexdigest()

        mock_client = MagicMock()
        mock_client.query.return_value = {
            "Items": [
                {
                    "github_id": {"S": "12345"},
                    "api_key_hash": {"S": key_hash},
                }
            ]
        }

        event = mock_event_factory(headers={"authorization": f"Bearer {dynamo_key}"})

        with (
            patch.dict(os.environ, {"USERS_TABLE_NAME": "mnemora-users-dev"}),
            patch.object(auth_mod, "_dynamo_client", mock_client),
        ):
            result = handler(event, mock_context)

        assert result["isAuthorized"] is True
        assert result["context"]["tenantId"] == "github:12345"
        mock_client.query.assert_called_once()

    def test_dynamo_lookup_rejects_unknown_key(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        """Key not in env vars and not in DynamoDB should be denied."""
        import handlers.auth as auth_mod

        mock_client = MagicMock()
        mock_client.query.return_value = {"Items": []}

        event = mock_event_factory(
            headers={"authorization": "Bearer mnm_unknown_key_xyz"}
        )

        with (
            patch.dict(os.environ, {"USERS_TABLE_NAME": "mnemora-users-dev"}),
            patch.object(auth_mod, "_dynamo_client", mock_client),
        ):
            result = handler(event, mock_context)

        assert result["isAuthorized"] is False

    def test_dynamo_lookup_skipped_without_table_name(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        """Without USERS_TABLE_NAME, DynamoDB lookup is skipped."""
        event = mock_event_factory(
            headers={"authorization": "Bearer mnm_no_table_configured"}
        )

        # Remove USERS_TABLE_NAME if set
        env = {k: v for k, v in os.environ.items() if k != "USERS_TABLE_NAME"}
        with patch.dict(os.environ, env, clear=True):
            result = handler(event, mock_context)

        assert result["isAuthorized"] is False

    def test_env_var_keys_still_work_with_dynamo_configured(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        """Env-var test keys should take priority over DynamoDB lookup."""
        event = mock_event_factory(
            headers={"authorization": f"Bearer {VALID_TEST_KEY}"}
        )

        with patch.dict(os.environ, {"USERS_TABLE_NAME": "mnemora-users-dev"}):
            result = handler(event, mock_context)

        assert result["isAuthorized"] is True
        assert result["context"]["tenantId"] == "test-tenant"

    def test_dynamo_error_returns_deny(
        self, mock_context: MagicMock, mock_event_factory: Any
    ) -> None:
        """DynamoDB errors should deny access, not crash."""
        import handlers.auth as auth_mod

        mock_client = MagicMock()
        mock_client.query.side_effect = Exception("DynamoDB unreachable")

        event = mock_event_factory(
            headers={"authorization": "Bearer mnm_error_test_key"}
        )

        with (
            patch.dict(os.environ, {"USERS_TABLE_NAME": "mnemora-users-dev"}),
            patch.object(auth_mod, "_dynamo_client", mock_client),
        ):
            result = handler(event, mock_context)

        assert result["isAuthorized"] is False
