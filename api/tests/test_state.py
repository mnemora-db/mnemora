"""Tests for api/handlers/state.py — working memory CRUD handler.

DynamoDB calls are intercepted by patching the lib.dynamo functions
directly — no boto3 or moto installation required in the test environment.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from handlers.state import _parse_path_segments, handler


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TENANT = "test-tenant"
_AGENT = "agent-001"
_SESSION = "sess-abc"
_REQUEST_ID = "test-request-id-12345"


def _state_item(
    agent_id: str = _AGENT,
    session_id: str = _SESSION,
    data: dict[str, Any] | None = None,
    version: int = 1,
) -> dict[str, Any]:
    """Return a clean state dict as returned by lib.dynamo functions."""
    return {
        "agent_id": agent_id,
        "session_id": session_id,
        "data": data or {"key": "value"},
        "version": version,
        "created_at": "2026-03-02T00:00:00+00:00",
        "updated_at": "2026-03-02T00:00:00+00:00",
        "expires_at": "2026-03-03T00:00:00+00:00",
    }


def _make_event(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    tenant_id: str = _TENANT,
    request_id: str = _REQUEST_ID,
    query_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a minimal API Gateway HTTP API v2 event for state tests."""
    event: dict[str, Any] = {
        "version": "2.0",
        "requestContext": {
            "requestId": request_id,
            "http": {"method": method, "path": path},
            "authorizer": {"lambda": {"tenantId": tenant_id}},
        },
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }
    if query_params is not None:
        event["queryStringParameters"] = query_params
    return event


# ---------------------------------------------------------------------------
# _parse_path_segments unit tests
# ---------------------------------------------------------------------------


class TestParsePathSegments:
    """Unit tests for the internal path-routing helper."""

    def test_root_path_returns_empty(self) -> None:
        assert _parse_path_segments("/v1/state") == []

    def test_root_path_with_trailing_slash_returns_empty(self) -> None:
        assert _parse_path_segments("/v1/state/") == []

    def test_agent_only_returns_one_segment(self) -> None:
        assert _parse_path_segments("/v1/state/agent-1") == ["agent-1"]

    def test_agent_sessions_returns_two_segments(self) -> None:
        assert _parse_path_segments("/v1/state/agent-1/sessions") == [
            "agent-1",
            "sessions",
        ]

    def test_agent_session_delete_returns_two_segments(self) -> None:
        assert _parse_path_segments("/v1/state/agent-1/sess-xyz") == [
            "agent-1",
            "sess-xyz",
        ]

    def test_unrelated_path_passes_through(self) -> None:
        # When the path does not start with /v1/state the whole path is split.
        result = _parse_path_segments("/v1/other/stuff")
        assert "other" in result


# ---------------------------------------------------------------------------
# POST /v1/state — create
# ---------------------------------------------------------------------------


class TestHandlerCreate:
    """Tests for POST /v1/state."""

    def test_create_returns_201(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/state",
            body={"agent_id": _AGENT, "data": {"x": 1}},
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()) as mock_put:
            result = handler(event, mock_context)

        assert result["statusCode"] == 201
        mock_put.assert_called_once()

    def test_create_response_has_data_and_meta(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/state",
            body={"agent_id": _AGENT, "data": {"x": 1}},
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert "data" in parsed
        assert "meta" in parsed
        assert parsed["meta"]["request_id"] == _REQUEST_ID

    def test_create_passes_tenant_id_not_from_body(
        self, mock_context: MagicMock
    ) -> None:
        """Tenant must come from authorizer, not request body."""
        event = _make_event(
            "POST",
            "/v1/state",
            body={"agent_id": _AGENT, "data": {}},
            tenant_id="real-tenant",
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()) as mock_put:
            handler(event, mock_context)

        call_kwargs = mock_put.call_args
        assert call_kwargs.kwargs["tenant_id"] == "real-tenant"

    def test_create_uses_provided_session_id(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/state",
            body={"agent_id": _AGENT, "session_id": "my-sess", "data": {}},
        )
        with patch(
            "lib.dynamo.put_state",
            return_value=_state_item(session_id="my-sess"),
        ) as mock_put:
            handler(event, mock_context)

        assert mock_put.call_args.kwargs["session_id"] == "my-sess"

    def test_create_generates_session_id_when_absent(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/state",
            body={"agent_id": _AGENT, "data": {}},
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()) as mock_put:
            handler(event, mock_context)

        session_id = mock_put.call_args.kwargs["session_id"]
        # Auto-generated UUID — must be a non-empty string
        assert isinstance(session_id, str)
        assert len(session_id) > 0

    def test_create_returns_400_when_agent_id_missing(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("POST", "/v1/state", body={"data": {"x": 1}})
        with patch("lib.dynamo.put_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_create_returns_400_when_agent_id_contains_hash(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/state",
            body={"agent_id": "bad#id", "data": {}},
        )
        with patch("lib.dynamo.put_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 400

    def test_create_returns_400_on_invalid_json(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", "/v1/state")
        event["body"] = "not-json{"
        with patch("lib.dynamo.put_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INVALID_JSON"

    def test_create_returns_413_on_oversized_body(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("POST", "/v1/state")
        # Craft a body string larger than 400 KB
        event["body"] = "x" * (400 * 1024 + 1)
        with patch("lib.dynamo.put_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 413
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "PAYLOAD_TOO_LARGE"

    def test_create_returns_400_when_ttl_hours_out_of_range(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/state",
            body={"agent_id": _AGENT, "data": {}, "ttl_hours": 9999},
        )
        with patch("lib.dynamo.put_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 400


# ---------------------------------------------------------------------------
# GET /v1/state/{agent_id}
# ---------------------------------------------------------------------------


class TestHandlerGet:
    """Tests for GET /v1/state/{agent_id}."""

    def test_get_returns_200_when_found(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        with patch("lib.dynamo.get_state", return_value=_state_item()):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_get_returns_state_data(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        expected = _state_item(data={"mood": "happy"})
        with patch("lib.dynamo.get_state", return_value=expected):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["data"] == {"mood": "happy"}

    def test_get_returns_404_when_not_found(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        with patch("lib.dynamo.get_state", return_value=None):
            result = handler(event, mock_context)

        assert result["statusCode"] == 404
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "NOT_FOUND"

    def test_get_uses_default_session(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        with patch("lib.dynamo.get_state", return_value=_state_item()) as mock_get:
            handler(event, mock_context)

        assert mock_get.call_args.kwargs["session_id"] == "default"

    def test_get_uses_session_id_from_query_param(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "GET", f"/v1/state/{_AGENT}", query_params={"session_id": "sess-xyz"}
        )
        with patch("lib.dynamo.get_state", return_value=_state_item()) as mock_get:
            handler(event, mock_context)

        assert mock_get.call_args.kwargs["session_id"] == "sess-xyz"

    def test_get_passes_correct_tenant_and_agent(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}", tenant_id="t-99")
        with patch("lib.dynamo.get_state", return_value=_state_item()) as mock_get:
            handler(event, mock_context)

        assert mock_get.call_args.kwargs["tenant_id"] == "t-99"
        assert mock_get.call_args.kwargs["agent_id"] == _AGENT

    def test_get_includes_request_id_in_meta(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        with patch("lib.dynamo.get_state", return_value=_state_item()):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID


# ---------------------------------------------------------------------------
# GET /v1/state/{agent_id}/sessions
# ---------------------------------------------------------------------------


class TestHandlerListSessions:
    """Tests for GET /v1/state/{agent_id}/sessions."""

    def test_list_sessions_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}/sessions")
        with patch("lib.dynamo.list_sessions", return_value=[_state_item()]):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_list_sessions_returns_all_sessions(self, mock_context: MagicMock) -> None:
        sessions = [_state_item(session_id="s1"), _state_item(session_id="s2")]
        event = _make_event("GET", f"/v1/state/{_AGENT}/sessions")
        with patch("lib.dynamo.list_sessions", return_value=sessions):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["count"] == 2
        assert len(parsed["data"]["sessions"]) == 2

    def test_list_sessions_returns_empty_list_when_no_sessions(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}/sessions")
        with patch("lib.dynamo.list_sessions", return_value=[]):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["count"] == 0
        assert parsed["data"]["sessions"] == []

    def test_list_sessions_includes_agent_id(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}/sessions")
        with patch("lib.dynamo.list_sessions", return_value=[]):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["agent_id"] == _AGENT

    def test_list_sessions_passes_tenant_and_agent_to_dynamo(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}/sessions", tenant_id="t-42")
        with patch("lib.dynamo.list_sessions", return_value=[]) as mock_list:
            handler(event, mock_context)

        assert mock_list.call_args.kwargs["tenant_id"] == "t-42"
        assert mock_list.call_args.kwargs["agent_id"] == _AGENT


# ---------------------------------------------------------------------------
# PUT /v1/state/{agent_id}
# ---------------------------------------------------------------------------


class TestHandlerUpdate:
    """Tests for PUT /v1/state/{agent_id}."""

    def test_update_returns_200_on_success(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "PUT",
            f"/v1/state/{_AGENT}",
            body={"session_id": _SESSION, "data": {"x": 2}, "version": 1},
        )
        with patch("lib.dynamo.update_state", return_value=_state_item(version=2)):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_update_increments_version_in_response(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "PUT",
            f"/v1/state/{_AGENT}",
            body={"session_id": _SESSION, "data": {}, "version": 3},
        )
        with patch("lib.dynamo.update_state", return_value=_state_item(version=4)):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["version"] == 4

    def test_update_returns_409_on_version_conflict(
        self, mock_context: MagicMock
    ) -> None:
        # Build a duck-typed exception that satisfies the handler's
        # botocore ClientError detection without importing botocore itself
        # (botocore is not installed in this test environment).
        class _FakeClientError(Exception):
            response = {
                "Error": {"Code": "ConditionalCheckFailedException", "Message": ""}
            }

        event = _make_event(
            "PUT",
            f"/v1/state/{_AGENT}",
            body={"session_id": _SESSION, "data": {}, "version": 1},
        )
        with patch("lib.dynamo.update_state", side_effect=_FakeClientError()):
            result = handler(event, mock_context)

        assert result["statusCode"] == 409
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VERSION_CONFLICT"

    def test_update_returns_400_when_version_missing(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "PUT",
            f"/v1/state/{_AGENT}",
            body={"session_id": _SESSION, "data": {}},  # version absent
        )
        with patch("lib.dynamo.update_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_update_returns_400_when_version_is_zero(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "PUT",
            f"/v1/state/{_AGENT}",
            body={"session_id": _SESSION, "data": {}, "version": 0},
        )
        with patch("lib.dynamo.update_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 400

    def test_update_passes_correct_expected_version(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "PUT",
            f"/v1/state/{_AGENT}",
            body={"session_id": _SESSION, "data": {}, "version": 7},
        )
        with patch(
            "lib.dynamo.update_state", return_value=_state_item(version=8)
        ) as mock_upd:
            handler(event, mock_context)

        assert mock_upd.call_args.kwargs["expected_version"] == 7

    def test_update_defaults_session_id_to_default(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "PUT",
            f"/v1/state/{_AGENT}",
            body={"data": {"k": "v"}, "version": 1},  # no session_id
        )
        with patch("lib.dynamo.update_state", return_value=_state_item()) as mock_upd:
            handler(event, mock_context)

        assert mock_upd.call_args.kwargs["session_id"] == "default"

    def test_update_returns_413_on_oversized_body(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("PUT", f"/v1/state/{_AGENT}")
        event["body"] = "x" * (400 * 1024 + 1)
        with patch("lib.dynamo.update_state"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 413


# ---------------------------------------------------------------------------
# DELETE /v1/state/{agent_id}/{session_id}
# ---------------------------------------------------------------------------


class TestHandlerDelete:
    """Tests for DELETE /v1/state/{agent_id}/{session_id}."""

    def test_delete_returns_200_when_found(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", f"/v1/state/{_AGENT}/{_SESSION}")
        with patch("lib.dynamo.delete_state", return_value=True):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_delete_response_contains_deleted_true(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("DELETE", f"/v1/state/{_AGENT}/{_SESSION}")
        with patch("lib.dynamo.delete_state", return_value=True):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["deleted"] is True

    def test_delete_response_contains_agent_and_session(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("DELETE", f"/v1/state/{_AGENT}/{_SESSION}")
        with patch("lib.dynamo.delete_state", return_value=True):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["agent_id"] == _AGENT
        assert parsed["data"]["session_id"] == _SESSION

    def test_delete_returns_404_when_not_found(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", f"/v1/state/{_AGENT}/{_SESSION}")
        with patch("lib.dynamo.delete_state", return_value=False):
            result = handler(event, mock_context)

        assert result["statusCode"] == 404
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "NOT_FOUND"

    def test_delete_passes_correct_tenant_agent_session(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "DELETE", f"/v1/state/{_AGENT}/{_SESSION}", tenant_id="t-77"
        )
        with patch("lib.dynamo.delete_state", return_value=True) as mock_del:
            handler(event, mock_context)

        assert mock_del.call_args.kwargs["tenant_id"] == "t-77"
        assert mock_del.call_args.kwargs["agent_id"] == _AGENT
        assert mock_del.call_args.kwargs["session_id"] == _SESSION


# ---------------------------------------------------------------------------
# Unknown / unmatched routes
# ---------------------------------------------------------------------------


class TestHandlerRouting:
    """Tests for unknown routes and method mismatches."""

    def test_unknown_route_returns_404(self, mock_context: MagicMock) -> None:
        event = _make_event("PATCH", "/v1/state/agent-1")
        result = handler(event, mock_context)

        assert result["statusCode"] == 404
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "NOT_FOUND"

    def test_unhandled_exception_returns_500(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        with patch("lib.dynamo.get_state", side_effect=RuntimeError("boom")):
            result = handler(event, mock_context)

        assert result["statusCode"] == 500
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INTERNAL_ERROR"
        # Raw exception message must NOT leak to clients
        assert "boom" not in parsed["error"]["message"]

    def test_500_response_includes_request_id(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        with patch("lib.dynamo.get_state", side_effect=RuntimeError("oops")):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID

    def test_all_responses_include_cors_headers(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/state/{_AGENT}")
        with patch("lib.dynamo.get_state", return_value=None):
            result = handler(event, mock_context)

        assert "Access-Control-Allow-Origin" in result["headers"]


# ---------------------------------------------------------------------------
# Models — unit tests for StateCreateRequest and StateUpdateRequest
# ---------------------------------------------------------------------------


class TestStateCreateRequest:
    """Unit tests for the StateCreateRequest Pydantic model."""

    def test_valid_request_parses(self) -> None:
        from lib.models import StateCreateRequest

        req = StateCreateRequest(agent_id="a1", data={"k": "v"})
        assert req.agent_id == "a1"
        assert req.data == {"k": "v"}

    def test_auto_generates_session_id(self) -> None:
        from lib.models import StateCreateRequest

        req = StateCreateRequest(agent_id="a1", data={})
        assert isinstance(req.session_id, str)
        assert len(req.session_id) > 0

    def test_rejects_hash_in_agent_id(self) -> None:
        from pydantic import ValidationError

        from lib.models import StateCreateRequest

        with pytest.raises(ValidationError):
            StateCreateRequest(agent_id="bad#id", data={})

    def test_rejects_hash_in_session_id(self) -> None:
        from pydantic import ValidationError

        from lib.models import StateCreateRequest

        with pytest.raises(ValidationError):
            StateCreateRequest(agent_id="ok", session_id="bad#sess", data={})

    def test_rejects_ttl_hours_above_max(self) -> None:
        from pydantic import ValidationError

        from lib.models import StateCreateRequest

        with pytest.raises(ValidationError):
            StateCreateRequest(agent_id="a", data={}, ttl_hours=8761)

    def test_rejects_ttl_hours_below_min(self) -> None:
        from pydantic import ValidationError

        from lib.models import StateCreateRequest

        with pytest.raises(ValidationError):
            StateCreateRequest(agent_id="a", data={}, ttl_hours=0)


class TestStateUpdateRequest:
    """Unit tests for the StateUpdateRequest Pydantic model."""

    def test_valid_request_parses(self) -> None:
        from lib.models import StateUpdateRequest

        req = StateUpdateRequest(data={"x": 1}, version=3)
        assert req.version == 3
        assert req.session_id == "default"

    def test_rejects_version_zero(self) -> None:
        from pydantic import ValidationError

        from lib.models import StateUpdateRequest

        with pytest.raises(ValidationError):
            StateUpdateRequest(data={}, version=0)

    def test_rejects_hash_in_session_id(self) -> None:
        from pydantic import ValidationError

        from lib.models import StateUpdateRequest

        with pytest.raises(ValidationError):
            StateUpdateRequest(session_id="bad#sess", data={}, version=1)
