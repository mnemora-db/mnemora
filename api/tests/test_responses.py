"""Tests for api/lib/responses.py — success and error response utilities."""

from __future__ import annotations

import json
import time

from lib.responses import CORS_HEADERS, error_response, success_response


class TestSuccessResponse:
    """Tests for success_response()."""

    def test_success_response_returns_200_by_default(self) -> None:
        # Arrange
        body = {"key": "value"}

        # Act
        result = success_response(body)

        # Assert
        assert result["statusCode"] == 200

    def test_success_response_returns_custom_status_code(self) -> None:
        # Arrange
        body = {"id": "abc"}

        # Act
        result = success_response(body, status=201)

        # Assert
        assert result["statusCode"] == 201

    def test_success_response_includes_cors_headers(self) -> None:
        # Arrange
        body = {}

        # Act
        result = success_response(body)

        # Assert
        for key, value in CORS_HEADERS.items():
            assert result["headers"][key] == value

    def test_success_response_body_has_data_and_meta(self) -> None:
        # Arrange
        body = {"status": "ok"}

        # Act
        result = success_response(body, request_id="req-123")
        parsed = json.loads(result["body"])

        # Assert
        assert "data" in parsed
        assert "meta" in parsed
        assert parsed["data"] == {"status": "ok"}
        assert parsed["meta"]["request_id"] == "req-123"

    def test_success_response_includes_request_id(self) -> None:
        # Arrange / Act
        result = success_response({}, request_id="my-req-id")
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["meta"]["request_id"] == "my-req-id"

    def test_success_response_calculates_latency_from_start_time(self) -> None:
        # Arrange
        start = time.time() - 0.05  # 50ms ago

        # Act
        result = success_response({}, start_time=start)
        parsed = json.loads(result["body"])

        # Assert — latency should be roughly 50ms (allow 10-200ms for test overhead)
        assert parsed["meta"]["latency_ms"] >= 10
        assert parsed["meta"]["latency_ms"] < 500

    def test_success_response_latency_zero_without_start_time(self) -> None:
        # Arrange / Act
        result = success_response({})
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["meta"]["latency_ms"] == 0

    def test_success_response_body_is_valid_json_string(self) -> None:
        # Arrange
        body = {"items": [1, 2, 3]}

        # Act
        result = success_response(body)

        # Assert
        parsed = json.loads(result["body"])
        assert parsed["data"]["items"] == [1, 2, 3]


class TestErrorResponse:
    """Tests for error_response()."""

    def test_error_response_returns_500_by_default(self) -> None:
        # Arrange / Act
        result = error_response(message="something broke")

        # Assert
        assert result["statusCode"] == 500

    def test_error_response_returns_custom_status_code(self) -> None:
        # Arrange / Act
        result = error_response(message="bad input", status=400)

        # Assert
        assert result["statusCode"] == 400

    def test_error_response_includes_cors_headers(self) -> None:
        # Arrange / Act
        result = error_response(message="fail")

        # Assert
        for key, value in CORS_HEADERS.items():
            assert result["headers"][key] == value

    def test_error_response_body_has_error_and_meta(self) -> None:
        # Arrange / Act
        result = error_response(
            message="not found",
            status=404,
            error_code="NOT_FOUND",
            request_id="req-456",
        )
        parsed = json.loads(result["body"])

        # Assert
        assert "error" in parsed
        assert "meta" in parsed
        assert parsed["error"]["code"] == "NOT_FOUND"
        assert parsed["error"]["message"] == "not found"
        assert parsed["meta"]["request_id"] == "req-456"

    def test_error_response_default_error_code_is_internal_error(self) -> None:
        # Arrange / Act
        result = error_response(message="oops")
        parsed = json.loads(result["body"])

        # Assert
        assert parsed["error"]["code"] == "INTERNAL_ERROR"

    def test_error_response_body_is_valid_json_string(self) -> None:
        # Arrange / Act
        result = error_response(message="test error", error_code="TEST")

        # Assert
        parsed = json.loads(result["body"])
        assert parsed["error"]["message"] == "test error"
