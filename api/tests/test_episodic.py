"""Tests for api/handlers/episodic.py, api/lib/episodes.py, and api/lib/summarizer.py.

All DynamoDB, S3, and Bedrock calls are intercepted by patching the relevant
lib functions directly — no real AWS credentials or database required.
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from handlers.episodic import _extract_request_id, _parse_body, handler


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TENANT = "test-tenant"
_AGENT = "agent-episodic-001"
_SESSION = "sess-ep-abc"
_REQUEST_ID = "req-episodic-12345"
_EPISODE_ID = str(uuid.uuid4())
_NOW = "2026-03-02T12:00:00+00:00"

_FAKE_EMBEDDING: list[float] = [0.1] * 1024


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_event(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    tenant_id: str = _TENANT,
    request_id: str = _REQUEST_ID,
    query_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a minimal API Gateway HTTP API v2 event for episodic tests."""
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


def _episode_item(
    episode_id: str = _EPISODE_ID,
    agent_id: str = _AGENT,
    session_id: str = _SESSION,
    episode_type: str = "conversation",
    content: str = "Hello, world.",
    metadata: dict[str, Any] | None = None,
    timestamp: str = _NOW,
) -> dict[str, Any]:
    """Return a clean episode dict as returned by lib.episodes functions."""
    return {
        "id": episode_id,
        "agent_id": agent_id,
        "session_id": session_id,
        "type": episode_type,
        "content": content,
        "metadata": metadata or {},
        "timestamp": timestamp,
    }


# ---------------------------------------------------------------------------
# _extract_request_id unit tests
# ---------------------------------------------------------------------------


class TestExtractRequestId:
    """Unit tests for the internal request-ID helper."""

    def test_extracts_known_request_id(self) -> None:
        event = _make_event("POST", "/v1/memory/episodic")
        assert _extract_request_id(event) == _REQUEST_ID

    def test_returns_unknown_when_missing(self) -> None:
        assert _extract_request_id({}) == "unknown"


# ---------------------------------------------------------------------------
# _parse_body unit tests
# ---------------------------------------------------------------------------


class TestParseBody:
    """Unit tests for the internal body-parsing helper."""

    def test_parses_valid_json(self) -> None:
        event = _make_event("POST", "/v1/memory/episodic", body={"key": "value"})
        assert _parse_body(event) == {"key": "value"}

    def test_returns_empty_dict_when_no_body(self) -> None:
        event = _make_event("POST", "/v1/memory/episodic")
        assert _parse_body(event) == {}

    def test_raises_on_invalid_json(self) -> None:
        import json as json_mod

        event = _make_event("POST", "/v1/memory/episodic")
        event["body"] = "not-valid-json{"
        with pytest.raises(json_mod.JSONDecodeError):
            _parse_body(event)


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


class TestHandlerRouting:
    """Tests for route matching logic in the episodic handler."""

    def test_unknown_route_returns_404(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", "/v1/memory/episodic/agent-1")
        result = handler(event, mock_context)
        assert result["statusCode"] == 404
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "NOT_FOUND"

    def test_unknown_method_returns_404(self, mock_context: MagicMock) -> None:
        event = _make_event("PATCH", "/v1/memory/episodic")
        result = handler(event, mock_context)
        assert result["statusCode"] == 404

    def test_all_responses_include_cors_headers(self, mock_context: MagicMock) -> None:
        event = _make_event("PATCH", "/v1/memory/episodic")
        result = handler(event, mock_context)
        assert "Access-Control-Allow-Origin" in result["headers"]

    def test_unhandled_exception_returns_500(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "conversation",
                "content": "hello",
            },
        )
        with patch("lib.episodes.put_episode", side_effect=RuntimeError("boom")):
            result = handler(event, mock_context)

        assert result["statusCode"] == 500
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INTERNAL_ERROR"
        # Raw exception message must NOT leak to clients.
        assert "boom" not in parsed["error"]["message"]

    def test_500_includes_request_id(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "conversation",
                "content": "hello",
            },
        )
        with patch("lib.episodes.put_episode", side_effect=RuntimeError("err")):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID


# ---------------------------------------------------------------------------
# POST /v1/memory/episodic — create
# ---------------------------------------------------------------------------


class TestHandlerCreate:
    """Tests for POST /v1/memory/episodic."""

    def test_create_returns_201(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "conversation",
                "content": "User said hello.",
            },
        )
        with patch("lib.episodes.put_episode", return_value=_episode_item()):
            result = handler(event, mock_context)

        assert result["statusCode"] == 201

    def test_create_response_has_data_and_meta(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "action",
                "content": "Called search_tool.",
            },
        )
        with patch("lib.episodes.put_episode", return_value=_episode_item()):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert "data" in parsed
        assert "meta" in parsed
        assert parsed["meta"]["request_id"] == _REQUEST_ID

    def test_create_passes_tenant_from_authorizer(
        self, mock_context: MagicMock
    ) -> None:
        """Tenant must come from authorizer context, never from request body."""
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "observation",
                "content": "Saw result.",
            },
            tenant_id="real-tenant",
        )
        with patch(
            "lib.episodes.put_episode", return_value=_episode_item()
        ) as mock_put:
            handler(event, mock_context)

        assert mock_put.call_args.kwargs["tenant_id"] == "real-tenant"

    def test_create_passes_correct_args(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "tool_call",
                "content": {"tool": "search", "query": "weather"},
                "metadata": {"source": "test"},
            },
        )
        with patch(
            "lib.episodes.put_episode", return_value=_episode_item()
        ) as mock_put:
            handler(event, mock_context)

        kwargs = mock_put.call_args.kwargs
        assert kwargs["agent_id"] == _AGENT
        assert kwargs["session_id"] == _SESSION
        assert kwargs["episode_type"] == "tool_call"
        assert kwargs["metadata"] == {"source": "test"}

    def test_create_returns_400_on_missing_agent_id(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={"session_id": _SESSION, "type": "conversation", "content": "hi"},
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_create_returns_400_on_missing_session_id(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={"agent_id": _AGENT, "type": "conversation", "content": "hi"},
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_create_returns_400_on_missing_type(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={"agent_id": _AGENT, "session_id": _SESSION, "content": "hi"},
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_create_returns_400_on_invalid_type(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "INVALID_TYPE",
                "content": "hi",
            },
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_create_returns_400_on_hash_in_agent_id(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": "bad#agent",
                "session_id": _SESSION,
                "type": "conversation",
                "content": "hi",
            },
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400

    def test_create_returns_400_on_hash_in_session_id(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": "bad#session",
                "type": "conversation",
                "content": "hi",
            },
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400

    def test_create_returns_400_on_invalid_json(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", "/v1/memory/episodic")
        event["body"] = "not-valid-json{"
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INVALID_JSON"

    def test_create_accepts_all_valid_types(self, mock_context: MagicMock) -> None:
        for ep_type in ("conversation", "action", "observation", "tool_call"):
            event = _make_event(
                "POST",
                "/v1/memory/episodic",
                body={
                    "agent_id": _AGENT,
                    "session_id": _SESSION,
                    "type": ep_type,
                    "content": "some content",
                },
            )
            with patch(
                "lib.episodes.put_episode",
                return_value=_episode_item(episode_type=ep_type),
            ):
                result = handler(event, mock_context)

            assert result["statusCode"] == 201

    def test_create_accepts_dict_content(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/episodic",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "type": "tool_call",
                "content": {"tool": "search", "args": {"q": "weather"}},
            },
        )
        with patch(
            "lib.episodes.put_episode",
            return_value=_episode_item(
                content={"tool": "search", "args": {"q": "weather"}}
            ),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 201


# ---------------------------------------------------------------------------
# GET /v1/memory/episodic/{agent_id}
# ---------------------------------------------------------------------------


class TestHandlerQuery:
    """Tests for GET /v1/memory/episodic/{agent_id}."""

    def test_query_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}")
        with patch("lib.episodes.query_episodes", return_value=[_episode_item()]):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_query_response_has_episodes_and_count(
        self, mock_context: MagicMock
    ) -> None:
        episodes = [_episode_item(), _episode_item(episode_id=str(uuid.uuid4()))]
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}")
        with patch("lib.episodes.query_episodes", return_value=episodes):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert "episodes" in parsed["data"]
        assert parsed["data"]["count"] == 2

    def test_query_returns_empty_list_when_no_episodes(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}")
        with patch("lib.episodes.query_episodes", return_value=[]):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["count"] == 0
        assert parsed["data"]["episodes"] == []

    def test_query_passes_from_and_to_params(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "GET",
            f"/v1/memory/episodic/{_AGENT}",
            query_params={"from": "2026-01-01T00:00:00+00:00", "to": _NOW},
        )
        with patch("lib.episodes.query_episodes", return_value=[]) as mock_q:
            handler(event, mock_context)

        kwargs = mock_q.call_args.kwargs
        assert kwargs["from_time"] == "2026-01-01T00:00:00+00:00"
        assert kwargs["to_time"] == _NOW

    def test_query_passes_type_filter(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "GET",
            f"/v1/memory/episodic/{_AGENT}",
            query_params={"type": "action"},
        )
        with patch("lib.episodes.query_episodes", return_value=[]) as mock_q:
            handler(event, mock_context)

        assert mock_q.call_args.kwargs["episode_type"] == "action"

    def test_query_passes_session_id_filter(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "GET",
            f"/v1/memory/episodic/{_AGENT}",
            query_params={"session_id": _SESSION},
        )
        with patch("lib.episodes.query_episodes", return_value=[]) as mock_q:
            handler(event, mock_context)

        assert mock_q.call_args.kwargs["session_id"] == _SESSION

    def test_query_passes_limit(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "GET",
            f"/v1/memory/episodic/{_AGENT}",
            query_params={"limit": "25"},
        )
        with patch("lib.episodes.query_episodes", return_value=[]) as mock_q:
            handler(event, mock_context)

        assert mock_q.call_args.kwargs["limit"] == 25

    def test_query_clamps_limit_to_max(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "GET",
            f"/v1/memory/episodic/{_AGENT}",
            query_params={"limit": "9999"},
        )
        with patch("lib.episodes.query_episodes", return_value=[]) as mock_q:
            handler(event, mock_context)

        assert mock_q.call_args.kwargs["limit"] == 500

    def test_query_defaults_limit_on_invalid_value(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "GET",
            f"/v1/memory/episodic/{_AGENT}",
            query_params={"limit": "not-a-number"},
        )
        with patch("lib.episodes.query_episodes", return_value=[]) as mock_q:
            handler(event, mock_context)

        assert mock_q.call_args.kwargs["limit"] == 50

    def test_query_passes_correct_tenant_and_agent(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "GET", f"/v1/memory/episodic/{_AGENT}", tenant_id="tenant-99"
        )
        with patch("lib.episodes.query_episodes", return_value=[]) as mock_q:
            handler(event, mock_context)

        assert mock_q.call_args.kwargs["tenant_id"] == "tenant-99"
        assert mock_q.call_args.kwargs["agent_id"] == _AGENT

    def test_query_includes_request_id_in_meta(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}")
        with patch("lib.episodes.query_episodes", return_value=[]):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID


# ---------------------------------------------------------------------------
# GET /v1/memory/episodic/{agent_id}/sessions/{session_id}
# ---------------------------------------------------------------------------


class TestHandlerSessionReplay:
    """Tests for GET /v1/memory/episodic/{agent_id}/sessions/{session_id}."""

    def test_session_replay_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}/sessions/{_SESSION}")
        with patch("lib.episodes.get_session_episodes", return_value=[_episode_item()]):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_session_replay_response_shape(self, mock_context: MagicMock) -> None:
        episodes = [_episode_item(), _episode_item(episode_id=str(uuid.uuid4()))]
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}/sessions/{_SESSION}")
        with patch("lib.episodes.get_session_episodes", return_value=episodes):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["session_id"] == _SESSION
        assert parsed["data"]["count"] == 2
        assert len(parsed["data"]["episodes"]) == 2

    def test_session_replay_empty_session(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}/sessions/{_SESSION}")
        with patch("lib.episodes.get_session_episodes", return_value=[]):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["count"] == 0
        assert parsed["data"]["episodes"] == []

    def test_session_replay_passes_correct_args(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "GET",
            f"/v1/memory/episodic/{_AGENT}/sessions/{_SESSION}",
            tenant_id="tenant-abc",
        )
        with patch("lib.episodes.get_session_episodes", return_value=[]) as mock_gse:
            handler(event, mock_context)

        kwargs = mock_gse.call_args.kwargs
        assert kwargs["tenant_id"] == "tenant-abc"
        assert kwargs["agent_id"] == _AGENT
        assert kwargs["session_id"] == _SESSION

    def test_session_replay_includes_request_id(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/episodic/{_AGENT}/sessions/{_SESSION}")
        with patch("lib.episodes.get_session_episodes", return_value=[]):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID


# ---------------------------------------------------------------------------
# POST /v1/memory/episodic/{agent_id}/summarize
# ---------------------------------------------------------------------------


class TestHandlerSummarize:
    """Tests for POST /v1/memory/episodic/{agent_id}/summarize."""

    _SUMMARY_RESULT: dict[str, Any] = {
        "summary": "The agent had a productive session.",
        "episode_count": 5,
        "semantic_memory_id": str(uuid.uuid4()),
        "time_range": {"from": _NOW, "to": _NOW},
    }

    def test_summarize_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", f"/v1/memory/episodic/{_AGENT}/summarize", body={})
        with patch(
            "lib.summarizer.summarize_episodes", return_value=self._SUMMARY_RESULT
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_summarize_response_has_summary_fields(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("POST", f"/v1/memory/episodic/{_AGENT}/summarize", body={})
        with patch(
            "lib.summarizer.summarize_episodes", return_value=self._SUMMARY_RESULT
        ):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["data"]["episode_count"] == 5
        assert "summary" in parsed["data"]
        assert "semantic_memory_id" in parsed["data"]

    def test_summarize_passes_defaults(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", f"/v1/memory/episodic/{_AGENT}/summarize", body={})
        with patch(
            "lib.summarizer.summarize_episodes", return_value=self._SUMMARY_RESULT
        ) as mock_sum:
            handler(event, mock_context)

        kwargs = mock_sum.call_args.kwargs
        assert kwargs["num_episodes"] == 50
        assert kwargs["target_length"] == 500

    def test_summarize_passes_custom_params(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            f"/v1/memory/episodic/{_AGENT}/summarize",
            body={"num_episodes": 100, "target_length": 1000},
        )
        with patch(
            "lib.summarizer.summarize_episodes", return_value=self._SUMMARY_RESULT
        ) as mock_sum:
            handler(event, mock_context)

        kwargs = mock_sum.call_args.kwargs
        assert kwargs["num_episodes"] == 100
        assert kwargs["target_length"] == 1000

    def test_summarize_passes_correct_tenant_and_agent(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            f"/v1/memory/episodic/{_AGENT}/summarize",
            body={},
            tenant_id="secure-tenant",
        )
        with patch(
            "lib.summarizer.summarize_episodes", return_value=self._SUMMARY_RESULT
        ) as mock_sum:
            handler(event, mock_context)

        kwargs = mock_sum.call_args.kwargs
        assert kwargs["tenant_id"] == "secure-tenant"
        assert kwargs["agent_id"] == _AGENT

    def test_summarize_returns_400_on_invalid_num_episodes(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            f"/v1/memory/episodic/{_AGENT}/summarize",
            body={"num_episodes": 0},
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_summarize_returns_400_on_num_episodes_too_large(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            f"/v1/memory/episodic/{_AGENT}/summarize",
            body={"num_episodes": 501},
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400

    def test_summarize_returns_400_on_target_length_too_small(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            f"/v1/memory/episodic/{_AGENT}/summarize",
            body={"target_length": 49},
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400

    def test_summarize_returns_400_on_invalid_json(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("POST", f"/v1/memory/episodic/{_AGENT}/summarize")
        event["body"] = "{{invalid"
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INVALID_JSON"

    def test_summarize_includes_request_id(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", f"/v1/memory/episodic/{_AGENT}/summarize", body={})
        with patch(
            "lib.summarizer.summarize_episodes", return_value=self._SUMMARY_RESULT
        ):
            result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID


# ---------------------------------------------------------------------------
# Models — EpisodeCreateRequest, EpisodeSummaryRequest, EpisodeResponse
# ---------------------------------------------------------------------------


class TestEpisodeCreateRequest:
    """Unit tests for the EpisodeCreateRequest Pydantic model."""

    def test_valid_request_parses(self) -> None:
        from lib.models import EpisodeCreateRequest

        req = EpisodeCreateRequest(
            agent_id=_AGENT,
            session_id=_SESSION,
            type="conversation",
            content="Hello",
        )
        assert req.agent_id == _AGENT
        assert req.session_id == _SESSION
        assert req.type == "conversation"
        assert req.content == "Hello"
        assert req.metadata == {}

    def test_all_valid_types_accepted(self) -> None:
        from lib.models import EpisodeCreateRequest

        for ep_type in ("conversation", "action", "observation", "tool_call"):
            req = EpisodeCreateRequest(
                agent_id=_AGENT,
                session_id=_SESSION,
                type=ep_type,
                content="x",
            )
            assert req.type == ep_type

    def test_invalid_type_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeCreateRequest

        with pytest.raises(ValidationError):
            EpisodeCreateRequest(
                agent_id=_AGENT,
                session_id=_SESSION,
                type="INVALID",
                content="x",
            )

    def test_hash_in_agent_id_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeCreateRequest

        with pytest.raises(ValidationError):
            EpisodeCreateRequest(
                agent_id="bad#id",
                session_id=_SESSION,
                type="conversation",
                content="x",
            )

    def test_hash_in_session_id_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeCreateRequest

        with pytest.raises(ValidationError):
            EpisodeCreateRequest(
                agent_id=_AGENT,
                session_id="bad#sess",
                type="conversation",
                content="x",
            )

    def test_missing_agent_id_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeCreateRequest

        with pytest.raises(ValidationError):
            EpisodeCreateRequest(  # type: ignore[call-arg]
                session_id=_SESSION, type="conversation", content="x"
            )

    def test_missing_session_id_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeCreateRequest

        with pytest.raises(ValidationError):
            EpisodeCreateRequest(  # type: ignore[call-arg]
                agent_id=_AGENT, type="conversation", content="x"
            )

    def test_missing_type_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeCreateRequest

        with pytest.raises(ValidationError):
            EpisodeCreateRequest(  # type: ignore[call-arg]
                agent_id=_AGENT, session_id=_SESSION, content="x"
            )

    def test_missing_content_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeCreateRequest

        with pytest.raises(ValidationError):
            EpisodeCreateRequest(  # type: ignore[call-arg]
                agent_id=_AGENT, session_id=_SESSION, type="conversation"
            )

    def test_dict_content_accepted(self) -> None:
        from lib.models import EpisodeCreateRequest

        req = EpisodeCreateRequest(
            agent_id=_AGENT,
            session_id=_SESSION,
            type="tool_call",
            content={"tool": "search", "query": "test"},
        )
        assert req.content == {"tool": "search", "query": "test"}

    def test_metadata_defaults_to_empty_dict(self) -> None:
        from lib.models import EpisodeCreateRequest

        req = EpisodeCreateRequest(
            agent_id=_AGENT, session_id=_SESSION, type="action", content="did thing"
        )
        assert req.metadata == {}

    def test_metadata_accepted(self) -> None:
        from lib.models import EpisodeCreateRequest

        req = EpisodeCreateRequest(
            agent_id=_AGENT,
            session_id=_SESSION,
            type="observation",
            content="saw thing",
            metadata={"source": "environment"},
        )
        assert req.metadata == {"source": "environment"}


class TestEpisodeSummaryRequest:
    """Unit tests for the EpisodeSummaryRequest Pydantic model."""

    def test_defaults_are_correct(self) -> None:
        from lib.models import EpisodeSummaryRequest

        req = EpisodeSummaryRequest()
        assert req.num_episodes == 50
        assert req.target_length == 500

    def test_custom_values_accepted(self) -> None:
        from lib.models import EpisodeSummaryRequest

        req = EpisodeSummaryRequest(num_episodes=100, target_length=1000)
        assert req.num_episodes == 100
        assert req.target_length == 1000

    def test_num_episodes_min_boundary(self) -> None:
        from lib.models import EpisodeSummaryRequest

        req = EpisodeSummaryRequest(num_episodes=1)
        assert req.num_episodes == 1

    def test_num_episodes_max_boundary(self) -> None:
        from lib.models import EpisodeSummaryRequest

        req = EpisodeSummaryRequest(num_episodes=500)
        assert req.num_episodes == 500

    def test_num_episodes_zero_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeSummaryRequest

        with pytest.raises(ValidationError):
            EpisodeSummaryRequest(num_episodes=0)

    def test_num_episodes_too_large_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeSummaryRequest

        with pytest.raises(ValidationError):
            EpisodeSummaryRequest(num_episodes=501)

    def test_target_length_min_boundary(self) -> None:
        from lib.models import EpisodeSummaryRequest

        req = EpisodeSummaryRequest(target_length=50)
        assert req.target_length == 50

    def test_target_length_max_boundary(self) -> None:
        from lib.models import EpisodeSummaryRequest

        req = EpisodeSummaryRequest(target_length=5000)
        assert req.target_length == 5000

    def test_target_length_too_small_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeSummaryRequest

        with pytest.raises(ValidationError):
            EpisodeSummaryRequest(target_length=49)

    def test_target_length_too_large_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import EpisodeSummaryRequest

        with pytest.raises(ValidationError):
            EpisodeSummaryRequest(target_length=5001)


class TestEpisodeResponse:
    """Unit tests for the EpisodeResponse Pydantic model."""

    def test_valid_response_parses(self) -> None:
        from lib.models import EpisodeResponse

        resp = EpisodeResponse(
            id=_EPISODE_ID,
            agent_id=_AGENT,
            session_id=_SESSION,
            type="conversation",
            content="Hello",
            metadata={},
            timestamp=_NOW,
        )
        assert resp.id == _EPISODE_ID
        assert resp.type == "conversation"

    def test_dict_content_preserved(self) -> None:
        from lib.models import EpisodeResponse

        resp = EpisodeResponse(
            id=_EPISODE_ID,
            agent_id=_AGENT,
            session_id=_SESSION,
            type="tool_call",
            content={"tool": "search"},
            metadata={},
            timestamp=_NOW,
        )
        assert resp.content == {"tool": "search"}


# ---------------------------------------------------------------------------
# lib.episodes — unit tests for storage functions
# ---------------------------------------------------------------------------


class TestPutEpisode:
    """Unit tests for lib.episodes.put_episode."""

    def test_returns_episode_dict_shape(self) -> None:
        from lib.episodes import put_episode

        mock_table = MagicMock()
        mock_table.put_item = MagicMock()

        with patch("lib.episodes._get_table", return_value=mock_table):
            result = put_episode(
                tenant_id=_TENANT,
                agent_id=_AGENT,
                session_id=_SESSION,
                episode_type="conversation",
                content="Hello world.",
            )

        assert "id" in result
        assert result["agent_id"] == _AGENT
        assert result["session_id"] == _SESSION
        assert result["type"] == "conversation"
        assert result["content"] == "Hello world."
        assert isinstance(result["timestamp"], str)

    def test_put_item_is_called(self) -> None:
        from lib.episodes import put_episode

        mock_table = MagicMock()

        with patch("lib.episodes._get_table", return_value=mock_table):
            put_episode(
                tenant_id=_TENANT,
                agent_id=_AGENT,
                session_id=_SESSION,
                episode_type="action",
                content="did something",
            )

        mock_table.put_item.assert_called_once()

    def test_item_has_pk_and_sk_structure(self) -> None:
        from lib.episodes import put_episode

        mock_table = MagicMock()
        captured_item: dict[str, Any] = {}

        def capture_put(Item: dict[str, Any]) -> None:  # noqa: N803
            captured_item.update(Item)

        mock_table.put_item.side_effect = capture_put

        with patch("lib.episodes._get_table", return_value=mock_table):
            put_episode(
                tenant_id=_TENANT,
                agent_id=_AGENT,
                session_id=_SESSION,
                episode_type="conversation",
                content="test",
            )

        assert captured_item["pk"] == f"{_TENANT}#{_AGENT}"
        assert captured_item["sk"].startswith("EPISODE#")
        assert captured_item["gsi1pk"] == f"{_TENANT}#{_SESSION}"
        assert "ttl" in captured_item

    def test_metadata_defaults_to_empty(self) -> None:
        from lib.episodes import put_episode

        mock_table = MagicMock()

        with patch("lib.episodes._get_table", return_value=mock_table):
            result = put_episode(
                tenant_id=_TENANT,
                agent_id=_AGENT,
                session_id=_SESSION,
                episode_type="observation",
                content="saw thing",
            )

        assert result["metadata"] == {}

    def test_metadata_is_stored(self) -> None:
        from lib.episodes import put_episode

        mock_table = MagicMock()

        with patch("lib.episodes._get_table", return_value=mock_table):
            result = put_episode(
                tenant_id=_TENANT,
                agent_id=_AGENT,
                session_id=_SESSION,
                episode_type="action",
                content="did thing",
                metadata={"source": "test"},
            )

        assert result["metadata"] == {"source": "test"}


class TestToEpisodeDict:
    """Unit tests for lib.episodes._to_episode_dict."""

    def test_extracts_agent_id_from_pk(self) -> None:
        from lib.episodes import _to_episode_dict

        item = {
            "pk": f"{_TENANT}#{_AGENT}",
            "sk": f"EPISODE#{_NOW}#{_EPISODE_ID}",
            "session_id": _SESSION,
            "episode_type": "conversation",
            "content": "hello",
            "metadata": {},
        }
        result = _to_episode_dict(item)
        assert result["agent_id"] == _AGENT

    def test_extracts_episode_id_from_sk(self) -> None:
        from lib.episodes import _to_episode_dict

        item = {
            "pk": f"{_TENANT}#{_AGENT}",
            "sk": f"EPISODE#{_NOW}#{_EPISODE_ID}",
            "session_id": _SESSION,
            "episode_type": "action",
            "content": "did",
            "metadata": {},
        }
        result = _to_episode_dict(item)
        assert result["id"] == _EPISODE_ID

    def test_extracts_timestamp_from_sk(self) -> None:
        from lib.episodes import _to_episode_dict

        item = {
            "pk": f"{_TENANT}#{_AGENT}",
            "sk": f"EPISODE#{_NOW}#{_EPISODE_ID}",
            "session_id": _SESSION,
            "episode_type": "observation",
            "content": "saw",
            "metadata": {},
        }
        result = _to_episode_dict(item)
        assert result["timestamp"] == _NOW


class TestQueryEpisodes:
    """Unit tests for lib.episodes.query_episodes."""

    def _make_dynamo_item(self, ep_type: str = "conversation") -> dict[str, Any]:
        return {
            "pk": f"{_TENANT}#{_AGENT}",
            "sk": f"EPISODE#{_NOW}#{_EPISODE_ID}",
            "gsi1pk": f"{_TENANT}#{_SESSION}",
            "gsi1sk": _NOW,
            "session_id": _SESSION,
            "episode_type": ep_type,
            "content": "hello",
            "metadata": {},
        }

    def _patch_conditions(self) -> MagicMock:
        """Return a MagicMock to stub boto3.dynamodb.conditions in sys.modules."""
        import sys

        mock_boto3 = MagicMock()
        mock_conditions = MagicMock()
        mock_boto3.dynamodb.conditions = mock_conditions
        sys.modules.setdefault("boto3", mock_boto3)
        sys.modules.setdefault("boto3.dynamodb", mock_boto3.dynamodb)
        sys.modules.setdefault("boto3.dynamodb.conditions", mock_conditions)
        return mock_conditions

    def test_returns_list_of_episode_dicts(self) -> None:
        from lib.episodes import query_episodes

        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": [self._make_dynamo_item()]}
        self._patch_conditions()

        with patch("lib.episodes._get_table", return_value=mock_table):
            results = query_episodes(tenant_id=_TENANT, agent_id=_AGENT)

        assert len(results) == 1
        assert results[0]["agent_id"] == _AGENT

    def test_returns_empty_list_when_no_items(self) -> None:
        from lib.episodes import query_episodes

        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        self._patch_conditions()

        with patch("lib.episodes._get_table", return_value=mock_table):
            results = query_episodes(tenant_id=_TENANT, agent_id=_AGENT)

        assert results == []

    def test_uses_gsi_when_session_id_provided(self) -> None:
        from lib.episodes import query_episodes

        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        self._patch_conditions()

        with patch("lib.episodes._get_table", return_value=mock_table):
            query_episodes(tenant_id=_TENANT, agent_id=_AGENT, session_id=_SESSION)

        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs.get("IndexName") == "session-index"


class TestGetSessionEpisodes:
    """Unit tests for lib.episodes.get_session_episodes."""

    def _patch_conditions(self) -> None:
        """Stub boto3.dynamodb.conditions in sys.modules for isolated testing."""
        import sys

        mock_boto3 = MagicMock()
        sys.modules.setdefault("boto3", mock_boto3)
        sys.modules.setdefault("boto3.dynamodb", mock_boto3.dynamodb)
        sys.modules.setdefault(
            "boto3.dynamodb.conditions", mock_boto3.dynamodb.conditions
        )

    def test_returns_episodes_in_order(self) -> None:
        from lib.episodes import get_session_episodes

        mock_table = MagicMock()
        items = [
            {
                "pk": f"{_TENANT}#{_AGENT}",
                "sk": f"EPISODE#{_NOW}#{_EPISODE_ID}",
                "session_id": _SESSION,
                "episode_type": "conversation",
                "content": "first",
                "metadata": {},
            }
        ]
        mock_table.query.return_value = {"Items": items}
        self._patch_conditions()

        with patch("lib.episodes._get_table", return_value=mock_table):
            results = get_session_episodes(
                tenant_id=_TENANT, agent_id=_AGENT, session_id=_SESSION
            )

        assert len(results) == 1

    def test_uses_gsi_session_index(self) -> None:
        from lib.episodes import get_session_episodes

        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        self._patch_conditions()

        with patch("lib.episodes._get_table", return_value=mock_table):
            get_session_episodes(
                tenant_id=_TENANT, agent_id=_AGENT, session_id=_SESSION
            )

        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs.get("IndexName") == "session-index"


class TestGetRecentEpisodes:
    """Unit tests for lib.episodes.get_recent_episodes."""

    def _patch_conditions(self) -> None:
        """Stub boto3.dynamodb.conditions in sys.modules for isolated testing."""
        import sys

        mock_boto3 = MagicMock()
        sys.modules.setdefault("boto3", mock_boto3)
        sys.modules.setdefault("boto3.dynamodb", mock_boto3.dynamodb)
        sys.modules.setdefault(
            "boto3.dynamodb.conditions", mock_boto3.dynamodb.conditions
        )

    def test_returns_episodes_in_chronological_order(self) -> None:
        from lib.episodes import get_recent_episodes

        mock_table = MagicMock()
        # DynamoDB returns newest-first; function reverses to chronological.
        items = [
            {
                "pk": f"{_TENANT}#{_AGENT}",
                "sk": "EPISODE#2026-03-02T12:00:00+00:00#id-2",
                "session_id": _SESSION,
                "episode_type": "action",
                "content": "second",
                "metadata": {},
            },
            {
                "pk": f"{_TENANT}#{_AGENT}",
                "sk": "EPISODE#2026-03-02T11:00:00+00:00#id-1",
                "session_id": _SESSION,
                "episode_type": "conversation",
                "content": "first",
                "metadata": {},
            },
        ]
        mock_table.query.return_value = {"Items": items}
        self._patch_conditions()

        with patch("lib.episodes._get_table", return_value=mock_table):
            results = get_recent_episodes(tenant_id=_TENANT, agent_id=_AGENT)

        # After reversing, "first" (older) should come before "second" (newer).
        assert results[0]["content"] == "first"
        assert results[1]["content"] == "second"

    def test_passes_limit_to_dynamo(self) -> None:
        from lib.episodes import get_recent_episodes

        mock_table = MagicMock()
        mock_table.query.return_value = {"Items": []}
        self._patch_conditions()

        with patch("lib.episodes._get_table", return_value=mock_table):
            get_recent_episodes(tenant_id=_TENANT, agent_id=_AGENT, limit=25)

        call_kwargs = mock_table.query.call_args.kwargs
        assert call_kwargs.get("Limit") == 25


class TestArchiveEpisodeToS3:
    """Unit tests for lib.episodes.archive_episode_to_s3."""

    def test_returns_s3_key_string(self) -> None:
        from lib.episodes import archive_episode_to_s3

        mock_s3 = MagicMock()
        mock_s3.put_object = MagicMock()

        episode = _episode_item()

        with patch("lib.episodes._get_s3_client", return_value=mock_s3):
            key = archive_episode_to_s3(
                tenant_id=_TENANT, agent_id=_AGENT, episode=episode
            )

        assert isinstance(key, str)
        assert _TENANT in key
        assert _AGENT in key
        assert key.endswith(".json.gz")

    def test_calls_s3_put_object(self) -> None:
        from lib.episodes import archive_episode_to_s3

        mock_s3 = MagicMock()
        episode = _episode_item()

        with patch("lib.episodes._get_s3_client", return_value=mock_s3):
            archive_episode_to_s3(tenant_id=_TENANT, agent_id=_AGENT, episode=episode)

        mock_s3.put_object.assert_called_once()

    def test_uses_gzip_content_encoding(self) -> None:
        from lib.episodes import archive_episode_to_s3

        mock_s3 = MagicMock()
        episode = _episode_item()

        with patch("lib.episodes._get_s3_client", return_value=mock_s3):
            archive_episode_to_s3(tenant_id=_TENANT, agent_id=_AGENT, episode=episode)

        call_kwargs = mock_s3.put_object.call_args.kwargs
        assert call_kwargs.get("ContentEncoding") == "gzip"


# ---------------------------------------------------------------------------
# lib.summarizer — unit tests
# ---------------------------------------------------------------------------


class TestSummarizeEpisodes:
    """Unit tests for lib.summarizer.summarize_episodes."""

    _FAKE_HAIKU_RESPONSE: dict[str, Any] = {
        "body": MagicMock(
            read=lambda: json.dumps(
                {"content": [{"text": "The agent was productive."}]}
            ).encode()
        )
    }

    def _run_summarize(
        self,
        episodes: list[dict[str, Any]],
        num_episodes: int = 50,
        target_length: int = 500,
    ) -> dict[str, Any]:
        """Helper: patch all external calls and run summarize_episodes."""
        from lib.summarizer import summarize_episodes

        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {"content": [{"text": "The agent was productive."}]}
                ).encode()
            )
        }

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = {"id": str(uuid.uuid4())}

        with (
            patch("lib.episodes.get_recent_episodes", return_value=episodes),
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.summarizer._get_bedrock_client", return_value=mock_bedrock),
            patch("lib.aurora.get_connection", return_value=mock_conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            return summarize_episodes(
                tenant_id=_TENANT,
                agent_id=_AGENT,
                num_episodes=num_episodes,
                target_length=target_length,
            )

    def test_returns_summary_dict(self) -> None:
        episodes = [_episode_item(), _episode_item(episode_id=str(uuid.uuid4()))]
        result = self._run_summarize(episodes)

        assert "summary" in result
        assert "episode_count" in result
        assert "semantic_memory_id" in result
        assert "time_range" in result

    def test_episode_count_matches_fetched_count(self) -> None:
        episodes = [_episode_item() for _ in range(5)]
        result = self._run_summarize(episodes)
        assert result["episode_count"] == 5

    def test_returns_empty_summary_when_no_episodes(self) -> None:
        result = self._run_summarize(episodes=[])
        assert result["episode_count"] == 0
        assert result["summary"] == ""
        assert result["semantic_memory_id"] is None
        assert result["time_range"] is None

    def test_haiku_is_called_with_prompt(self) -> None:
        from lib.summarizer import summarize_episodes

        mock_bedrock = MagicMock()
        mock_bedrock.invoke_model.return_value = {
            "body": MagicMock(
                read=lambda: json.dumps(
                    {"content": [{"text": "Summary here."}]}
                ).encode()
            )
        }

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = {"id": str(uuid.uuid4())}

        episodes = [_episode_item()]

        with (
            patch("lib.episodes.get_recent_episodes", return_value=episodes),
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.summarizer._get_bedrock_client", return_value=mock_bedrock),
            patch("lib.aurora.get_connection", return_value=mock_conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            summarize_episodes(
                tenant_id=_TENANT, agent_id=_AGENT, num_episodes=10, target_length=200
            )

        mock_bedrock.invoke_model.assert_called_once()
        call_kwargs = mock_bedrock.invoke_model.call_args.kwargs
        assert call_kwargs["modelId"] == "anthropic.claude-3-haiku-20240307-v1:0"

    def test_time_range_computed_from_episodes(self) -> None:
        episodes = [
            _episode_item(timestamp="2026-03-01T10:00:00+00:00"),
            _episode_item(
                episode_id=str(uuid.uuid4()),
                timestamp="2026-03-02T12:00:00+00:00",
            ),
        ]
        result = self._run_summarize(episodes)
        assert result["time_range"] is not None
        assert result["time_range"]["from"] == "2026-03-01T10:00:00+00:00"
        assert result["time_range"]["to"] == "2026-03-02T12:00:00+00:00"

    def test_summary_text_from_haiku_is_returned(self) -> None:
        episodes = [_episode_item()]
        result = self._run_summarize(episodes)
        assert result["summary"] == "The agent was productive."
