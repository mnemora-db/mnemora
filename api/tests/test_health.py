"""Tests for api/handlers/health.py — health check endpoint."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

from handlers.health import VERSION, handler


class TestHealthHandler:
    """Tests for the health check handler."""

    def test_health_returns_200(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange — use default fixtures

        # Act
        result = handler(mock_event, mock_context)

        # Assert
        assert result["statusCode"] == 200

    def test_health_returns_correct_json_structure(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange — use default fixtures

        # Act
        result = handler(mock_event, mock_context)
        parsed = json.loads(result["body"])

        # Assert — top-level keys
        assert "data" in parsed
        assert "meta" in parsed

        # Assert — data keys
        assert "status" in parsed["data"]
        assert "version" in parsed["data"]
        assert "timestamp" in parsed["data"]

        # Assert — meta keys
        assert "request_id" in parsed["meta"]
        assert "latency_ms" in parsed["meta"]

    def test_health_returns_status_ok(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange / Act
        result = handler(mock_event, mock_context)
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["data"]["status"] == "ok"

    def test_health_returns_version_0_1_0(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange / Act
        result = handler(mock_event, mock_context)
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["data"]["version"] == "0.1.0"
        assert VERSION == "0.1.0"

    def test_health_returns_valid_iso_timestamp(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange / Act
        result = handler(mock_event, mock_context)
        parsed = json.loads(result["body"])
        timestamp_str = parsed["data"]["timestamp"]

        # Assert — should parse without error as ISO format
        parsed_dt = datetime.fromisoformat(timestamp_str)
        assert parsed_dt is not None
        assert parsed_dt.year >= 2024

    def test_health_includes_request_id_from_event(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange — mock_event has requestId "test-request-id-12345"

        # Act
        result = handler(mock_event, mock_context)
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["meta"]["request_id"] == "test-request-id-12345"

    def test_health_request_id_defaults_to_unknown(
        self, mock_context: MagicMock
    ) -> None:
        # Arrange — event with no requestContext
        event: dict[str, Any] = {}

        # Act
        result = handler(event, mock_context)
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["meta"]["request_id"] == "unknown"

    def test_health_includes_cors_headers(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange / Act
        result = handler(mock_event, mock_context)

        # Assert
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["headers"]["Access-Control-Allow-Origin"] == "*"
        assert "GET" in result["headers"]["Access-Control-Allow-Methods"]

    def test_health_latency_is_non_negative(
        self, mock_event: dict[str, Any], mock_context: MagicMock
    ) -> None:
        # Arrange / Act
        result = handler(mock_event, mock_context)
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["meta"]["latency_ms"] >= 0
