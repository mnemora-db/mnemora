"""Tests for api/handlers/unified.py and api/lib/usage.py.

All AWS / Aurora / Bedrock calls are intercepted by patching the relevant
lib functions directly — no real credentials or network access required.

Coverage:
- POST /v1/memory auto-routing (state, episodic, semantic, unknown → 400)
- GET  /v1/memory/{agent_id} combined view with partial failure handling
- POST /v1/memory/search cross-memory merge
- DELETE /v1/memory/{agent_id} GDPR purge
- GET  /v1/usage usage stats
- lib.usage module unit tests
- Model validation for UnifiedMemoryCreateRequest and UnifiedSearchRequest
"""

from __future__ import annotations

import json
import uuid
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from handlers.unified import handler


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TENANT = "test-tenant"
_AGENT = "agent-unified-001"
_SESSION = "sess-unified-abc"
_REQUEST_ID = "req-unified-12345"
_NOW = "2026-03-02T12:00:00+00:00"
_MEMORY_ID = str(uuid.uuid4())
_EPISODE_ID = str(uuid.uuid4())
_FAKE_EMBEDDING: list[float] = [0.1] * 1024


# ---------------------------------------------------------------------------
# Event builder
# ---------------------------------------------------------------------------


def _make_event(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    tenant_id: str = _TENANT,
    request_id: str = _REQUEST_ID,
    query_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a minimal API Gateway HTTP API v2 event for unified tests."""
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
# Fixture data factories
# ---------------------------------------------------------------------------


def _state_item(
    agent_id: str = _AGENT,
    session_id: str = _SESSION,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "agent_id": agent_id,
        "session_id": session_id,
        "data": data or {"key": "value"},
        "version": 1,
        "created_at": _NOW,
        "updated_at": _NOW,
        "expires_at": None,
    }


def _episode_item(
    agent_id: str = _AGENT,
    episode_id: str = _EPISODE_ID,
    content: str = "The user asked about the weather",
    episode_type: str = "conversation",
) -> dict[str, Any]:
    return {
        "id": episode_id,
        "agent_id": agent_id,
        "session_id": _SESSION,
        "type": episode_type,
        "content": content,
        "metadata": {},
        "timestamp": _NOW,
    }


def _semantic_row(
    memory_id: str = _MEMORY_ID,
    agent_id: str = _AGENT,
    content: str = "The agent learned that the user prefers dark mode",
) -> dict[str, Any]:
    return {
        "id": memory_id,
        "agent_id": agent_id,
        "namespace": "default",
        "content": content,
        "metadata": {},
        "similarity": 0.87,
        "created_at": _NOW,
        "updated_at": _NOW,
    }


# ---------------------------------------------------------------------------
# Helpers: mock Aurora cursor context manager
# ---------------------------------------------------------------------------


def _make_mock_cursor(fetchone_val: Any = None, fetchall_val: Any = None) -> MagicMock:
    """Build a mock psycopg cursor usable as a context manager."""
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone_val
    cursor.fetchall.return_value = fetchall_val or []
    cursor.rowcount = 0
    cursor.__enter__ = lambda s: s
    cursor.__exit__ = MagicMock(return_value=False)
    return cursor


def _make_mock_conn(cursor: MagicMock) -> MagicMock:
    """Build a mock psycopg connection usable as a context manager."""
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = lambda s: s
    conn.__exit__ = MagicMock(return_value=False)
    return conn


# ---------------------------------------------------------------------------
# POST /v1/memory — auto-routing tests
# ---------------------------------------------------------------------------


class TestHandlerCreateAutoRouting:
    """Tests for POST /v1/memory auto-routing logic."""

    # --- State routing ---

    def test_routes_to_state_when_data_and_session_id(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "data": {"mood": "happy"},
            },
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()) as mock_put:
            result = handler(event, mock_context)

        assert result["statusCode"] == 201
        mock_put.assert_called_once()
        body = json.loads(result["body"])
        assert body["data"]["memory_type"] == "state"

    def test_state_routing_uses_authorizer_tenant_not_body(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "data": {},
            },
            tenant_id="real-tenant",
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()) as mock_put:
            handler(event, mock_context)

        assert mock_put.call_args.kwargs["tenant_id"] == "real-tenant"

    def test_state_routing_response_has_meta_request_id(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": _AGENT, "session_id": _SESSION, "data": {}},
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["meta"]["request_id"] == _REQUEST_ID

    # --- Episodic routing ---

    def test_routes_to_episodic_when_content_and_episode_type(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={
                "agent_id": _AGENT,
                "content": "User asked about the weather",
                "type": "conversation",
            },
        )
        with patch(
            "lib.episodes.put_episode", return_value=_episode_item()
        ) as mock_put:
            result = handler(event, mock_context)

        assert result["statusCode"] == 201
        mock_put.assert_called_once()
        body = json.loads(result["body"])
        assert body["data"]["memory_type"] == "episodic"

    def test_episodic_routing_all_type_values(self, mock_context: MagicMock) -> None:
        episode_types = ["conversation", "action", "observation", "tool_call"]
        for ep_type in episode_types:
            event = _make_event(
                "POST",
                "/v1/memory",
                body={
                    "agent_id": _AGENT,
                    "content": f"Episode of type {ep_type}",
                    "type": ep_type,
                },
            )
            ep_item = _episode_item(episode_type=ep_type)
            with patch("lib.episodes.put_episode", return_value=ep_item):
                result = handler(event, mock_context)
            assert result["statusCode"] == 201, f"Expected 201 for type={ep_type}"

    def test_unknown_episode_type_returns_400(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={
                "agent_id": _AGENT,
                "content": "Some content",
                "type": "unknown_type",
            },
        )
        with patch("lib.episodes.put_episode"):
            result = handler(event, mock_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    # --- Semantic routing ---

    def test_routes_to_semantic_when_content_only(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": _AGENT, "content": "User prefers dark mode"},
        )
        cursor = _make_mock_cursor()
        # First fetchone (dedup check) → None; second fetchone (INSERT) → row
        inserted_row = dict(_semantic_row())
        cursor.fetchone.side_effect = [None, inserted_row]
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["data"]["memory_type"] == "semantic"

    def test_semantic_routing_dedup_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": _AGENT, "content": "User prefers dark mode"},
        )
        existing = {"id": _MEMORY_ID, "metadata": {}}
        updated_row = dict(_semantic_row())
        cursor = _make_mock_cursor()
        cursor.fetchone.side_effect = [existing, updated_row]
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 201
        body = json.loads(result["body"])
        assert body["data"]["deduplicated"] is True
        assert body["data"]["memory_type"] == "semantic"

    # --- Unroutable payload ---

    def test_returns_400_when_payload_unroutable(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": _AGENT},  # no data, no content
        )
        result = handler(event, mock_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"]["code"] == "UNROUTABLE_PAYLOAD"

    def test_returns_400_for_invalid_json(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", "/v1/memory")
        event["body"] = "not-valid-json{"
        result = handler(event, mock_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"]["code"] == "INVALID_JSON"

    def test_returns_400_when_agent_id_missing(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"content": "some text"},  # no agent_id
        )
        result = handler(event, mock_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_returns_400_when_agent_id_contains_hash(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": "bad#id", "content": "text"},
        )
        result = handler(event, mock_context)

        assert result["statusCode"] == 400

    def test_error_message_includes_routing_hints(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": _AGENT},
        )
        result = handler(event, mock_context)

        body = json.loads(result["body"])
        # Message should explain what's needed for each memory type.
        assert "working memory" in body["error"]["message"].lower()
        assert "semantic memory" in body["error"]["message"].lower()


# ---------------------------------------------------------------------------
# GET /v1/memory/{agent_id} — combined view
# ---------------------------------------------------------------------------


class TestHandlerGetAgent:
    """Tests for GET /v1/memory/{agent_id}."""

    def _full_mock_get(
        self,
        state: dict[str, Any] | None,
        semantic_rows: list[dict[str, Any]],
        episodes: list[dict[str, Any]],
    ) -> tuple[Any, Any, Any, Any]:
        """Return patch targets for all three stores."""
        cursor = _make_mock_cursor(fetchall_val=semantic_rows)
        conn = _make_mock_conn(cursor)
        return (
            patch("lib.dynamo.get_state", return_value=state),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=episodes),
        )

    def test_get_returns_200_with_all_stores(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[_semantic_row()])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=_state_item()),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[_episode_item()]),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        data = body["data"]
        assert data["state"] is not None
        assert len(data["semantic"]) == 1
        assert len(data["episodic"]) == 1

    def test_get_response_includes_summary(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[_semantic_row()])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=_state_item()),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        summary = body["data"]["summary"]
        assert summary["state_exists"] is True
        assert summary["semantic_count"] == 1
        assert summary["episodic_count"] == 0

    def test_get_returns_null_state_when_not_found(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=None),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["data"]["state"] is None
        assert body["data"]["summary"]["state_exists"] is False

    def test_get_partial_failure_state_store_adds_warning(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", side_effect=RuntimeError("DynamoDB down")),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        # Should still return 200 with partial data.
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "warnings" in body["data"]
        assert any("working memory" in w.lower() for w in body["data"]["warnings"])

    def test_get_partial_failure_aurora_store_adds_warning(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")

        with (
            patch("lib.dynamo.get_state", return_value=_state_item()),
            patch("lib.aurora.get_connection", side_effect=RuntimeError("Aurora down")),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "warnings" in body["data"]
        assert any("semantic" in w.lower() for w in body["data"]["warnings"])

    def test_get_partial_failure_episodic_store_adds_warning(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=None),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch(
                "lib.episodes.query_episodes",
                side_effect=RuntimeError("Episodes down"),
            ),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert "warnings" in body["data"]
        assert any("episodic" in w.lower() for w in body["data"]["warnings"])

    def test_get_no_warnings_when_all_succeed(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=None),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert "warnings" not in body["data"]

    def test_get_includes_agent_id_in_response(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=None),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["data"]["agent_id"] == _AGENT

    def test_get_includes_request_id_in_meta(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=None),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["meta"]["request_id"] == _REQUEST_ID


# ---------------------------------------------------------------------------
# POST /v1/memory/search — cross-memory search
# ---------------------------------------------------------------------------


class TestHandlerSearch:
    """Tests for POST /v1/memory/search."""

    def test_search_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "dark mode preference"},
        )
        sem_row = dict(_semantic_row())
        sem_row["similarity"] = 0.82
        cursor = _make_mock_cursor(fetchall_val=[sem_row])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_search_semantic_results_have_memory_type(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "dark mode"},
        )
        sem_row = dict(_semantic_row())
        sem_row["similarity"] = 0.82
        cursor = _make_mock_cursor(fetchall_val=[sem_row])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        for r in body["data"]["results"]:
            if r["memory_type"] == "semantic":
                assert "similarity_score" in r

    def test_search_episodic_results_have_relevance_field(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "weather"},
        )
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)
        ep = _episode_item(content="The user asked about the weather today")

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[ep]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        episodic_results = [
            r for r in body["data"]["results"] if r["memory_type"] == "episodic"
        ]
        assert len(episodic_results) >= 1
        assert episodic_results[0]["relevance"] == "text_match"

    def test_search_semantic_results_appear_before_episodic(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "weather"},
        )
        sem_row = dict(_semantic_row())
        sem_row["similarity"] = 0.75
        cursor = _make_mock_cursor(fetchall_val=[sem_row])
        conn = _make_mock_conn(cursor)
        ep = _episode_item(content="User asked about the weather today")

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[ep]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        results = body["data"]["results"]
        if len(results) >= 2:
            assert results[0]["memory_type"] == "semantic"

    def test_search_returns_count_field(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "anything"},
        )
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert "count" in body["data"]
        assert body["data"]["count"] == len(body["data"]["results"])

    def test_search_filters_by_agent_id(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "topic", "agent_id": _AGENT},
        )
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]) as mock_ep,
        ):
            handler(event, mock_context)

        # Episodic query should receive the agent_id filter.
        assert mock_ep.call_args.kwargs["agent_id"] == _AGENT

    def test_search_returns_400_when_query_missing(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"top_k": 5},  # no query
        )
        result = handler(event, mock_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"]["code"] == "VALIDATION_ERROR"

    def test_search_returns_400_for_invalid_json(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", "/v1/memory/search")
        event["body"] = "{{broken"
        result = handler(event, mock_context)

        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert body["error"]["code"] == "INVALID_JSON"

    def test_search_returns_empty_results_when_no_matches(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "obscure topic no one writes about"},
        )
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["data"]["results"] == []
        assert body["data"]["count"] == 0

    def test_search_includes_request_id_in_meta(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "test"},
            request_id="search-req-abc",
        )
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["meta"]["request_id"] == "search-req-abc"

    def test_search_continues_when_semantic_store_fails(
        self, mock_context: MagicMock
    ) -> None:
        """Search should return episodic results even if Aurora is down."""
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "weather"},
        )
        ep = _episode_item(content="The user asked about the weather")

        with (
            patch(
                "lib.embeddings.generate_embedding",
                side_effect=RuntimeError("Bedrock down"),
            ),
            patch("lib.episodes.query_episodes", return_value=[ep]),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        # Episodic results should still be returned.
        assert body["data"]["count"] >= 1

    def test_search_continues_when_episodic_store_fails(
        self, mock_context: MagicMock
    ) -> None:
        """Search should return semantic results even if DynamoDB is down."""
        event = _make_event(
            "POST",
            "/v1/memory/search",
            body={"query": "dark mode"},
        )
        sem_row = dict(_semantic_row())
        sem_row["similarity"] = 0.80
        cursor = _make_mock_cursor(fetchall_val=[sem_row])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch(
                "lib.episodes.query_episodes",
                side_effect=RuntimeError("DynamoDB down"),
            ),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["data"]["count"] >= 1


# ---------------------------------------------------------------------------
# DELETE /v1/memory/{agent_id} — GDPR purge
# ---------------------------------------------------------------------------


class TestHandlerPurge:
    """Tests for DELETE /v1/memory/{agent_id}.

    The DynamoDB and S3 operations are extracted into private helper functions
    (_purge_dynamo_items, _purge_s3_objects) that are patched here without
    requiring boto3 to be installed in the test environment.
    """

    def _make_purge_patches(
        self,
        dynamo_counts: dict[str, int] | None = None,
        s3_count: int = 0,
        aurora_rowcount: int = 0,
    ) -> tuple[Any, Any, Any, Any]:
        """Return patch context managers for all purge stores."""
        counts = dynamo_counts or {"state": 0, "episodic": 0}
        cursor = _make_mock_cursor()
        cursor.rowcount = aurora_rowcount
        conn = _make_mock_conn(cursor)
        return (
            patch("handlers.unified._purge_dynamo_items", return_value=counts),
            patch("handlers.unified._purge_s3_objects", return_value=s3_count),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        )

    def test_purge_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", f"/v1/memory/{_AGENT}")

        with (
            patch(
                "handlers.unified._purge_dynamo_items",
                return_value={"state": 0, "episodic": 0},
            ),
            patch("handlers.unified._purge_s3_objects", return_value=0),
            patch(
                "lib.aurora.get_connection",
                return_value=_make_mock_conn(_make_mock_cursor()),
            ),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_purge_response_has_deleted_counts(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor()
        cursor.rowcount = 3
        conn = _make_mock_conn(cursor)

        with (
            patch(
                "handlers.unified._purge_dynamo_items",
                return_value={"state": 1, "episodic": 1},
            ),
            patch("handlers.unified._purge_s3_objects", return_value=0),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        deleted = body["data"]["deleted"]
        assert "state" in deleted
        assert "episodic" in deleted
        assert "semantic" in deleted
        assert "s3_objects" in deleted

    def test_purge_counts_state_and_episodic_separately(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("DELETE", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor()
        cursor.rowcount = 0
        conn = _make_mock_conn(cursor)

        with (
            patch(
                "handlers.unified._purge_dynamo_items",
                return_value={"state": 2, "episodic": 1},
            ),
            patch("handlers.unified._purge_s3_objects", return_value=0),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        deleted = body["data"]["deleted"]
        assert deleted["state"] == 2
        assert deleted["episodic"] == 1

    def test_purge_counts_s3_objects(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor()
        cursor.rowcount = 0
        conn = _make_mock_conn(cursor)

        with (
            patch(
                "handlers.unified._purge_dynamo_items",
                return_value={"state": 0, "episodic": 0},
            ),
            patch("handlers.unified._purge_s3_objects", return_value=5),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["data"]["deleted"]["s3_objects"] == 5

    def test_purge_is_idempotent_when_no_data(self, mock_context: MagicMock) -> None:
        """Calling purge on an agent with no data should succeed with zeros."""
        event = _make_event("DELETE", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor()
        cursor.rowcount = 0
        conn = _make_mock_conn(cursor)

        with (
            patch(
                "handlers.unified._purge_dynamo_items",
                return_value={"state": 0, "episodic": 0},
            ),
            patch("handlers.unified._purge_s3_objects", return_value=0),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        deleted = body["data"]["deleted"]
        assert deleted["state"] == 0
        assert deleted["episodic"] == 0

    def test_purge_includes_agent_id_in_response(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor()
        cursor.rowcount = 0
        conn = _make_mock_conn(cursor)

        with (
            patch(
                "handlers.unified._purge_dynamo_items",
                return_value={"state": 0, "episodic": 0},
            ),
            patch("handlers.unified._purge_s3_objects", return_value=0),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["data"]["agent_id"] == _AGENT

    def test_purge_includes_request_id_in_meta(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "DELETE", f"/v1/memory/{_AGENT}", request_id="purge-req-xyz"
        )
        cursor = _make_mock_cursor()
        cursor.rowcount = 0
        conn = _make_mock_conn(cursor)

        with (
            patch(
                "handlers.unified._purge_dynamo_items",
                return_value={"state": 0, "episodic": 0},
            ),
            patch("handlers.unified._purge_s3_objects", return_value=0),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["meta"]["request_id"] == "purge-req-xyz"


# ---------------------------------------------------------------------------
# GET /v1/usage
# ---------------------------------------------------------------------------


class TestHandlerUsage:
    """Tests for GET /v1/usage.

    The DynamoDB scan is extracted into _get_dynamo_usage_stats which is
    patched here — no boto3 installation required.
    """

    def _make_usage_response(self) -> dict[str, Any]:
        return {
            "api_calls": 150,
            "embeddings": 42,
            "storage_bytes": 0,
            "month": "2026-03",
        }

    _dynamo_stats = {
        "dynamo_items": 10,
        "agents_count": 2,
        "sessions_count": 5,
    }

    def test_usage_returns_200(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", "/v1/usage")
        cursor = _make_mock_cursor(fetchone_val={"cnt": 7})
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.usage.get_usage", return_value=self._make_usage_response()),
            patch(
                "handlers.unified._get_dynamo_usage_stats",
                return_value=self._dynamo_stats,
            ),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_usage_response_shape(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", "/v1/usage")
        cursor = _make_mock_cursor(fetchone_val={"cnt": 3})
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.usage.get_usage", return_value=self._make_usage_response()),
            patch(
                "handlers.unified._get_dynamo_usage_stats",
                return_value=self._dynamo_stats,
            ),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        data = body["data"]
        assert "api_calls_month" in data
        assert "embeddings_generated_month" in data
        assert "storage" in data
        assert "agents_count" in data
        assert "sessions_count" in data
        assert "billing_period" in data
        assert "dynamodb_items" in data["storage"]
        assert "semantic_memories" in data["storage"]

    def test_usage_returns_correct_api_calls(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", "/v1/usage")
        cursor = _make_mock_cursor(fetchone_val={"cnt": 0})
        conn = _make_mock_conn(cursor)
        usage_data = self._make_usage_response()
        usage_data["api_calls"] = 999

        with (
            patch("lib.usage.get_usage", return_value=usage_data),
            patch(
                "handlers.unified._get_dynamo_usage_stats",
                return_value=self._dynamo_stats,
            ),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["data"]["api_calls_month"] == 999

    def test_usage_includes_request_id_in_meta(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", "/v1/usage", request_id="usage-req-123")
        cursor = _make_mock_cursor(fetchone_val={"cnt": 0})
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.usage.get_usage", return_value=self._make_usage_response()),
            patch(
                "handlers.unified._get_dynamo_usage_stats",
                return_value=self._dynamo_stats,
            ),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["meta"]["request_id"] == "usage-req-123"

    def test_usage_graceful_when_aurora_fails(self, mock_context: MagicMock) -> None:
        """Usage endpoint should still return 200 if Aurora count fails."""
        event = _make_event("GET", "/v1/usage")

        with (
            patch("lib.usage.get_usage", return_value=self._make_usage_response()),
            patch(
                "handlers.unified._get_dynamo_usage_stats",
                return_value=self._dynamo_stats,
            ),
            patch(
                "lib.aurora.get_connection",
                side_effect=RuntimeError("Aurora down"),
            ),
            patch("lib.aurora.set_tenant_context"),
        ):
            result = handler(event, mock_context)

        assert result["statusCode"] == 200

    def test_usage_uses_authorizer_tenant_id(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", "/v1/usage", tenant_id="specific-tenant")
        cursor = _make_mock_cursor(fetchone_val={"cnt": 0})
        conn = _make_mock_conn(cursor)

        with (
            patch(
                "lib.usage.get_usage", return_value=self._make_usage_response()
            ) as mock_usage,
            patch(
                "handlers.unified._get_dynamo_usage_stats",
                return_value=self._dynamo_stats,
            ),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
        ):
            handler(event, mock_context)

        assert mock_usage.call_args.args[0] == "specific-tenant"


# ---------------------------------------------------------------------------
# Routing and error cases
# ---------------------------------------------------------------------------


class TestHandlerRouting:
    """Tests for routing, unknown routes, and error handling."""

    def test_unknown_route_returns_404(self, mock_context: MagicMock) -> None:
        event = _make_event("PATCH", "/v1/memory/agent-1")
        result = handler(event, mock_context)

        assert result["statusCode"] == 404
        body = json.loads(result["body"])
        assert body["error"]["code"] == "NOT_FOUND"

    def test_unhandled_exception_returns_500(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": _AGENT, "session_id": _SESSION, "data": {}},
        )
        with patch("lib.dynamo.put_state", side_effect=RuntimeError("boom")):
            result = handler(event, mock_context)

        assert result["statusCode"] == 500
        body = json.loads(result["body"])
        assert body["error"]["code"] == "INTERNAL_ERROR"
        # Raw exception message must NOT appear in the response.
        assert "boom" not in body["error"]["message"]

    def test_500_includes_request_id_in_meta(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory",
            body={"agent_id": _AGENT, "session_id": _SESSION, "data": {}},
            request_id="error-req-999",
        )
        with patch("lib.dynamo.put_state", side_effect=RuntimeError("oops")):
            result = handler(event, mock_context)

        body = json.loads(result["body"])
        assert body["meta"]["request_id"] == "error-req-999"

    def test_all_responses_include_cors_headers(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/{_AGENT}")
        cursor = _make_mock_cursor(fetchall_val=[])
        conn = _make_mock_conn(cursor)

        with (
            patch("lib.dynamo.get_state", return_value=None),
            patch("lib.aurora.get_connection", return_value=conn),
            patch("lib.aurora.set_tenant_context"),
            patch("lib.episodes.query_episodes", return_value=[]),
        ):
            result = handler(event, mock_context)

        assert "Access-Control-Allow-Origin" in result["headers"]

    def test_tenant_id_always_from_authorizer(self, mock_context: MagicMock) -> None:
        """Verify the handler never trusts a body-level tenant_id."""
        event = _make_event(
            "POST",
            "/v1/memory",
            body={
                "agent_id": _AGENT,
                "session_id": _SESSION,
                "data": {},
                # Attacker tries to set their own tenant_id in the body.
                "tenant_id": "evil-tenant",
            },
            tenant_id="real-tenant",
        )
        with patch("lib.dynamo.put_state", return_value=_state_item()) as mock_put:
            handler(event, mock_context)

        assert mock_put.call_args.kwargs["tenant_id"] == "real-tenant"


# ---------------------------------------------------------------------------
# lib.usage module unit tests
# ---------------------------------------------------------------------------


class TestUsageModule:
    """Unit tests for api/lib/usage.py."""

    def test_increment_counter_calls_update_item(self) -> None:
        from lib.usage import increment_counter

        table = MagicMock()
        with patch("lib.usage._get_table", return_value=table):
            increment_counter("tenant-1", "api_calls", amount=3)

        table.update_item.assert_called_once()
        call_kwargs = table.update_item.call_args.kwargs
        assert "ADD" in call_kwargs["UpdateExpression"]
        assert call_kwargs["ExpressionAttributeValues"][":amount"] == 3

    def test_increment_counter_default_amount_is_one(self) -> None:
        from lib.usage import increment_counter

        table = MagicMock()
        with patch("lib.usage._get_table", return_value=table):
            increment_counter("t", "api_calls")

        call_kwargs = table.update_item.call_args.kwargs
        assert call_kwargs["ExpressionAttributeValues"][":amount"] == 1

    def test_increment_counter_pk_contains_usage(self) -> None:
        from lib.usage import increment_counter

        table = MagicMock()
        with patch("lib.usage._get_table", return_value=table):
            increment_counter("my-tenant", "embeddings")

        key = table.update_item.call_args.kwargs["Key"]
        assert "my-tenant" in key["pk"]
        assert "USAGE" in key["pk"]

    def test_increment_counter_sk_contains_month(self) -> None:
        from lib.usage import increment_counter

        table = MagicMock()
        with patch("lib.usage._get_table", return_value=table):
            increment_counter("t", "api_calls")

        key = table.update_item.call_args.kwargs["Key"]
        assert key["sk"].startswith("MONTH#")

    def test_get_usage_returns_dict_with_counters(self) -> None:
        from lib.usage import get_usage

        item = {
            "pk": "tenant-1#USAGE",
            "sk": "MONTH#2026-03",
            "api_calls": 100,
            "embeddings": 20,
            "storage_bytes": 5000,
        }
        table = MagicMock()
        table.get_item.return_value = {"Item": item}

        with patch("lib.usage._get_table", return_value=table):
            result = get_usage("tenant-1")

        assert result["api_calls"] == 100
        assert result["embeddings"] == 20
        assert result["storage_bytes"] == 5000

    def test_get_usage_defaults_to_zero_when_no_item(self) -> None:
        from lib.usage import get_usage

        table = MagicMock()
        table.get_item.return_value = {}  # no Item key

        with patch("lib.usage._get_table", return_value=table):
            result = get_usage("new-tenant")

        assert result["api_calls"] == 0
        assert result["embeddings"] == 0
        assert result["storage_bytes"] == 0

    def test_get_usage_includes_month_field(self) -> None:
        from lib.usage import get_usage

        table = MagicMock()
        table.get_item.return_value = {}

        with patch("lib.usage._get_table", return_value=table):
            result = get_usage("t")

        assert "month" in result
        # Should be a YYYY-MM format string.
        assert len(result["month"]) == 7

    def test_get_usage_queries_correct_pk(self) -> None:
        from lib.usage import get_usage

        table = MagicMock()
        table.get_item.return_value = {}

        with patch("lib.usage._get_table", return_value=table):
            get_usage("my-tenant")

        key = table.get_item.call_args.kwargs["Key"]
        assert "my-tenant" in key["pk"]
        assert "USAGE" in key["pk"]

    def test_usage_table_caches_after_first_call(self) -> None:
        """The module-level _table is set on first call and reused thereafter.

        When _table is None, _get_table initialises it.  When _table is
        already set, _get_table returns it immediately without re-creating
        the boto3 resource.  We verify this by calling get_usage twice with
        _table pre-populated and confirming get_item is called twice (once
        per get_usage call) on the same mock table object.
        """
        import lib.usage as usage_module

        original_table = usage_module._table

        table = MagicMock()
        table.get_item.return_value = {}

        try:
            # Pre-set the module-level cache.
            usage_module._table = table

            from lib.usage import get_usage

            get_usage("t")
            get_usage("t")
        finally:
            usage_module._table = original_table

        # get_item should have been called once per get_usage call, both
        # against the same table object — proving the cache was reused.
        assert table.get_item.call_count == 2


# ---------------------------------------------------------------------------
# Pydantic model unit tests
# ---------------------------------------------------------------------------


class TestUnifiedMemoryCreateRequest:
    """Unit tests for UnifiedMemoryCreateRequest Pydantic model."""

    def test_valid_state_payload(self) -> None:
        from lib.models import UnifiedMemoryCreateRequest

        req = UnifiedMemoryCreateRequest(
            agent_id=_AGENT,
            session_id=_SESSION,
            data={"k": "v"},
        )
        assert req.data == {"k": "v"}
        assert req.session_id == _SESSION

    def test_valid_semantic_payload(self) -> None:
        from lib.models import UnifiedMemoryCreateRequest

        req = UnifiedMemoryCreateRequest(
            agent_id=_AGENT,
            content="User prefers dark mode",
        )
        assert req.content == "User prefers dark mode"
        assert req.type is None

    def test_valid_episodic_payload(self) -> None:
        from lib.models import UnifiedMemoryCreateRequest

        req = UnifiedMemoryCreateRequest(
            agent_id=_AGENT,
            content="User asked about weather",
            type="conversation",
        )
        assert req.type == "conversation"

    def test_rejects_agent_id_with_hash(self) -> None:
        from pydantic import ValidationError

        from lib.models import UnifiedMemoryCreateRequest

        with pytest.raises(ValidationError):
            UnifiedMemoryCreateRequest(agent_id="bad#id", content="text")

    def test_rejects_session_id_with_hash(self) -> None:
        from pydantic import ValidationError

        from lib.models import UnifiedMemoryCreateRequest

        with pytest.raises(ValidationError):
            UnifiedMemoryCreateRequest(agent_id=_AGENT, session_id="bad#sess", data={})

    def test_rejects_ttl_hours_above_max(self) -> None:
        from pydantic import ValidationError

        from lib.models import UnifiedMemoryCreateRequest

        with pytest.raises(ValidationError):
            UnifiedMemoryCreateRequest(agent_id=_AGENT, content="text", ttl_hours=9000)

    def test_metadata_defaults_to_empty_dict(self) -> None:
        from lib.models import UnifiedMemoryCreateRequest

        req = UnifiedMemoryCreateRequest(agent_id=_AGENT, content="text")
        assert req.metadata == {}

    def test_namespace_defaults_to_default(self) -> None:
        from lib.models import UnifiedMemoryCreateRequest

        req = UnifiedMemoryCreateRequest(agent_id=_AGENT, content="text")
        assert req.namespace == "default"


class TestUnifiedSearchRequest:
    """Unit tests for UnifiedSearchRequest Pydantic model."""

    def test_valid_minimal_request(self) -> None:
        from lib.models import UnifiedSearchRequest

        req = UnifiedSearchRequest(query="dark mode")
        assert req.query == "dark mode"
        assert req.top_k == 10
        assert req.threshold == 0.5

    def test_rejects_empty_query(self) -> None:
        from pydantic import ValidationError

        from lib.models import UnifiedSearchRequest

        with pytest.raises(ValidationError):
            UnifiedSearchRequest(query="")

    def test_rejects_top_k_above_100(self) -> None:
        from pydantic import ValidationError

        from lib.models import UnifiedSearchRequest

        with pytest.raises(ValidationError):
            UnifiedSearchRequest(query="x", top_k=101)

    def test_rejects_threshold_above_1(self) -> None:
        from pydantic import ValidationError

        from lib.models import UnifiedSearchRequest

        with pytest.raises(ValidationError):
            UnifiedSearchRequest(query="x", threshold=1.1)

    def test_agent_id_is_optional(self) -> None:
        from lib.models import UnifiedSearchRequest

        req = UnifiedSearchRequest(query="test")
        assert req.agent_id is None

    def test_agent_id_can_be_set(self) -> None:
        from lib.models import UnifiedSearchRequest

        req = UnifiedSearchRequest(query="test", agent_id=_AGENT)
        assert req.agent_id == _AGENT
