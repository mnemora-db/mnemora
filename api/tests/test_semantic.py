"""Tests for api/handlers/semantic.py and api/lib/embeddings.py.

All Aurora and Bedrock calls are intercepted by patching the relevant
lib functions directly — no real AWS credentials or database required.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from handlers.semantic import handler, _extract_request_id, _row_to_response


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_TENANT = "test-tenant"
_AGENT = "agent-001"
_REQUEST_ID = "test-request-id-99999"
_MEMORY_ID = str(uuid.uuid4())
_NOW = "2026-03-02T00:00:00+00:00"

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
) -> dict[str, Any]:
    """Build a minimal API Gateway HTTP API v2 event for semantic tests."""
    return {
        "version": "2.0",
        "requestContext": {
            "requestId": request_id,
            "http": {"method": method, "path": path},
            "authorizer": {"lambda": {"tenantId": tenant_id}},
        },
        "body": json.dumps(body) if body is not None else None,
        "isBase64Encoded": False,
    }


def _make_db_row(
    memory_id: str = _MEMORY_ID,
    agent_id: str = _AGENT,
    namespace: str = "default",
    content: str = "The user's name is Alice.",
    metadata: dict[str, Any] | None = None,
    similarity: float | None = None,
) -> dict[str, Any]:
    """Return a fake psycopg dict_row for semantic_memory."""
    row: dict[str, Any] = {
        "id": memory_id,
        "agent_id": agent_id,
        "namespace": namespace,
        "content": content,
        "metadata": metadata or {},
        "created_at": datetime(2026, 3, 2, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 3, 2, tzinfo=timezone.utc),
    }
    if similarity is not None:
        row["similarity"] = similarity
    return row


# ---------------------------------------------------------------------------
# _extract_request_id unit tests
# ---------------------------------------------------------------------------


class TestExtractRequestId:
    """Unit tests for the internal request-ID helper."""

    def test_extracts_known_request_id(self) -> None:
        event = _make_event("GET", "/v1/memory/semantic")
        assert _extract_request_id(event) == _REQUEST_ID

    def test_returns_unknown_when_missing(self) -> None:
        assert _extract_request_id({}) == "unknown"


# ---------------------------------------------------------------------------
# _row_to_response unit tests
# ---------------------------------------------------------------------------


class TestRowToResponse:
    """Unit tests for the DB row → response dict converter."""

    def test_basic_fields_are_present(self) -> None:
        row = _make_db_row()
        result = _row_to_response(row)
        assert result["id"] == _MEMORY_ID
        assert result["agent_id"] == _AGENT
        assert result["content"] == "The user's name is Alice."
        assert result["namespace"] == "default"
        assert result["metadata"] == {}
        assert result["similarity_score"] is None
        assert result["deduplicated"] is False

    def test_similarity_score_is_forwarded(self) -> None:
        row = _make_db_row()
        result = _row_to_response(row, similarity_score=0.87)
        assert result["similarity_score"] == pytest.approx(0.87)

    def test_deduplicated_flag_is_forwarded(self) -> None:
        row = _make_db_row()
        result = _row_to_response(row, deduplicated=True)
        assert result["deduplicated"] is True

    def test_datetime_converted_to_iso_string(self) -> None:
        row = _make_db_row()
        result = _row_to_response(row)
        assert isinstance(result["created_at"], str)
        assert "2026" in result["created_at"]

    def test_string_timestamp_passed_through(self) -> None:
        row = _make_db_row()
        row["created_at"] = "2026-03-02T00:00:00+00:00"
        result = _row_to_response(row)
        assert result["created_at"] == "2026-03-02T00:00:00+00:00"

    def test_none_timestamp_becomes_empty_string(self) -> None:
        row = _make_db_row()
        row["created_at"] = None
        result = _row_to_response(row)
        assert result["created_at"] == ""

    def test_none_metadata_becomes_empty_dict(self) -> None:
        row = _make_db_row()
        row["metadata"] = None
        result = _row_to_response(row)
        assert result["metadata"] == {}


# ---------------------------------------------------------------------------
# Routing tests
# ---------------------------------------------------------------------------


class TestHandlerRouting:
    """Tests for route matching logic."""

    def test_unknown_route_returns_404(self, mock_context: MagicMock) -> None:
        event = _make_event("PATCH", "/v1/memory/semantic/some-id")
        result = handler(event, mock_context)
        assert result["statusCode"] == 404
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "NOT_FOUND"

    def test_all_responses_include_cors_headers(self, mock_context: MagicMock) -> None:
        event = _make_event("PATCH", "/v1/memory/semantic")
        result = handler(event, mock_context)
        assert "Access-Control-Allow-Origin" in result["headers"]

    def test_unhandled_exception_returns_500(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/semantic",
            body={"agent_id": _AGENT, "content": "hello"},
        )
        with patch(
            "lib.embeddings.generate_embedding", side_effect=RuntimeError("kaboom")
        ):
            with patch("lib.aurora.get_connection"):
                result = handler(event, mock_context)

        assert result["statusCode"] == 500
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INTERNAL_ERROR"
        # Raw exception message must NOT leak to clients.
        assert "kaboom" not in parsed["error"]["message"]

    def test_500_response_includes_request_id(self, mock_context: MagicMock) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/semantic",
            body={"agent_id": _AGENT, "content": "hello"},
        )
        with patch(
            "lib.embeddings.generate_embedding", side_effect=RuntimeError("err")
        ):
            with patch("lib.aurora.get_connection"):
                result = handler(event, mock_context)

        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID


# ---------------------------------------------------------------------------
# POST /v1/memory/semantic — create
# ---------------------------------------------------------------------------


class TestHandlerCreate:
    """Tests for POST /v1/memory/semantic."""

    def _run_create(
        self,
        mock_context: MagicMock,
        body: dict[str, Any],
        db_row: dict[str, Any] | None = None,
        existing_row: dict[str, Any] | None = None,
        tenant_id: str = _TENANT,
    ) -> dict[str, Any]:
        """Helper: patch Aurora and Bedrock, then call the handler."""
        if db_row is None:
            db_row = _make_db_row()

        event = _make_event(
            "POST", "/v1/memory/semantic", body=body, tenant_id=tenant_id
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)

        # First fetchone call → dedup check result; second → INSERT result.
        mock_cursor.fetchone.side_effect = [existing_row, db_row]

        with patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING):
            with patch("lib.aurora.get_connection", return_value=mock_conn):
                with patch("lib.aurora.set_tenant_context"):
                    return handler(event, mock_context)

    def test_create_returns_201(self, mock_context: MagicMock) -> None:
        result = self._run_create(
            mock_context, {"agent_id": _AGENT, "content": "Remember this."}
        )
        assert result["statusCode"] == 201

    def test_create_response_has_data_and_meta(self, mock_context: MagicMock) -> None:
        result = self._run_create(
            mock_context, {"agent_id": _AGENT, "content": "Remember this."}
        )
        parsed = json.loads(result["body"])
        assert "data" in parsed
        assert "meta" in parsed
        assert parsed["meta"]["request_id"] == _REQUEST_ID

    def test_create_response_deduplicated_is_false(
        self, mock_context: MagicMock
    ) -> None:
        result = self._run_create(
            mock_context, {"agent_id": _AGENT, "content": "Something new."}
        )
        parsed = json.loads(result["body"])
        assert parsed["data"]["deduplicated"] is False

    def test_create_uses_authorizer_tenant_not_body(
        self, mock_context: MagicMock
    ) -> None:
        """Tenant must come from authorizer context, never from request body."""
        result = self._run_create(
            mock_context,
            {"agent_id": _AGENT, "content": "content"},
            tenant_id="real-tenant",
        )
        # Only checking that the call succeeds with the injected tenant.
        assert result["statusCode"] == 201

    def test_create_returns_200_when_deduplicated(
        self, mock_context: MagicMock
    ) -> None:
        existing = _make_db_row()
        result = self._run_create(
            mock_context,
            {"agent_id": _AGENT, "content": "Same content."},
            existing_row=existing,
        )
        parsed = json.loads(result["body"])
        assert result["statusCode"] == 200
        assert parsed["data"]["deduplicated"] is True

    def test_create_returns_400_on_missing_agent_id(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("POST", "/v1/memory/semantic", body={"content": "no agent"})
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_create_returns_400_on_missing_content(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event("POST", "/v1/memory/semantic", body={"agent_id": _AGENT})
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_create_returns_400_on_invalid_json(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", "/v1/memory/semantic")
        event["body"] = "not-valid-json{"
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INVALID_JSON"

    def test_create_uses_default_namespace(self, mock_context: MagicMock) -> None:
        result = self._run_create(
            mock_context, {"agent_id": _AGENT, "content": "content"}
        )
        parsed = json.loads(result["body"])
        assert parsed["data"]["namespace"] == "default"

    def test_create_accepts_custom_namespace(self, mock_context: MagicMock) -> None:
        db_row = _make_db_row(namespace="facts")
        result = self._run_create(
            mock_context,
            {"agent_id": _AGENT, "content": "content", "namespace": "facts"},
            db_row=db_row,
        )
        parsed = json.loads(result["body"])
        assert parsed["data"]["namespace"] == "facts"

    def test_create_top_k_out_of_range_ignored_at_create(
        self, mock_context: MagicMock
    ) -> None:
        """top_k is not a create field; extra keys should be silently ignored."""
        result = self._run_create(
            mock_context,
            {"agent_id": _AGENT, "content": "content", "top_k": 9999},
        )
        # Pydantic will ignore unknown fields by default (extra='ignore').
        assert result["statusCode"] == 201


# ---------------------------------------------------------------------------
# POST /v1/memory/semantic/search
# ---------------------------------------------------------------------------


class TestHandlerSearch:
    """Tests for POST /v1/memory/semantic/search."""

    def _run_search(
        self,
        mock_context: MagicMock,
        body: dict[str, Any],
        db_rows: list[dict[str, Any]] | None = None,
        tenant_id: str = _TENANT,
    ) -> dict[str, Any]:
        """Helper: patch Aurora and Bedrock, then call the handler."""
        if db_rows is None:
            db_rows = [_make_db_row(similarity=0.85)]

        event = _make_event(
            "POST",
            "/v1/memory/semantic/search",
            body=body,
            tenant_id=tenant_id,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchall.return_value = db_rows

        with patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING):
            with patch("lib.aurora.get_connection", return_value=mock_conn):
                with patch("lib.aurora.set_tenant_context"):
                    return handler(event, mock_context)

    def test_search_returns_200(self, mock_context: MagicMock) -> None:
        result = self._run_search(mock_context, {"query": "Alice's name"})
        assert result["statusCode"] == 200

    def test_search_response_has_results_and_count(
        self, mock_context: MagicMock
    ) -> None:
        result = self._run_search(mock_context, {"query": "Alice's name"})
        parsed = json.loads(result["body"])
        assert "results" in parsed["data"]
        assert "count" in parsed["data"]
        assert parsed["data"]["count"] == 1

    def test_search_includes_similarity_score(self, mock_context: MagicMock) -> None:
        result = self._run_search(mock_context, {"query": "Alice's name"})
        parsed = json.loads(result["body"])
        assert parsed["data"]["results"][0]["similarity_score"] == pytest.approx(0.85)

    def test_search_returns_empty_list_when_no_matches(
        self, mock_context: MagicMock
    ) -> None:
        result = self._run_search(mock_context, {"query": "unknown"}, db_rows=[])
        parsed = json.loads(result["body"])
        assert parsed["data"]["count"] == 0
        assert parsed["data"]["results"] == []

    def test_search_response_includes_request_id(self, mock_context: MagicMock) -> None:
        result = self._run_search(mock_context, {"query": "hello"})
        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID

    def test_search_returns_400_on_missing_query(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", "/v1/memory/semantic/search", body={"top_k": 5})
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "VALIDATION_ERROR"

    def test_search_returns_400_when_top_k_exceeds_100(
        self, mock_context: MagicMock
    ) -> None:
        event = _make_event(
            "POST",
            "/v1/memory/semantic/search",
            body={"query": "test", "top_k": 101},
        )
        result = handler(event, mock_context)
        assert result["statusCode"] == 400

    def test_search_returns_400_on_invalid_json(self, mock_context: MagicMock) -> None:
        event = _make_event("POST", "/v1/memory/semantic/search")
        event["body"] = "{{invalid"
        result = handler(event, mock_context)
        assert result["statusCode"] == 400
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "INVALID_JSON"

    def test_search_uses_authorizer_tenant(self, mock_context: MagicMock) -> None:
        result = self._run_search(
            mock_context,
            {"query": "test"},
            tenant_id="secure-tenant",
        )
        assert result["statusCode"] == 200


# ---------------------------------------------------------------------------
# GET /v1/memory/semantic/{id}
# ---------------------------------------------------------------------------


class TestHandlerGet:
    """Tests for GET /v1/memory/semantic/{id}."""

    def _run_get(
        self,
        mock_context: MagicMock,
        memory_id: str = _MEMORY_ID,
        db_row: dict[str, Any] | None = None,
        tenant_id: str = _TENANT,
    ) -> dict[str, Any]:
        event = _make_event(
            "GET",
            f"/v1/memory/semantic/{memory_id}",
            tenant_id=tenant_id,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = db_row or _make_db_row()

        with patch("lib.aurora.get_connection", return_value=mock_conn):
            with patch("lib.aurora.set_tenant_context"):
                return handler(event, mock_context)

    def test_get_returns_200_when_found(self, mock_context: MagicMock) -> None:
        result = self._run_get(mock_context)
        assert result["statusCode"] == 200

    def test_get_response_has_data_and_meta(self, mock_context: MagicMock) -> None:
        result = self._run_get(mock_context)
        parsed = json.loads(result["body"])
        assert "data" in parsed
        assert "meta" in parsed
        assert parsed["meta"]["request_id"] == _REQUEST_ID

    def test_get_returns_correct_memory_id(self, mock_context: MagicMock) -> None:
        result = self._run_get(mock_context)
        parsed = json.loads(result["body"])
        assert parsed["data"]["id"] == _MEMORY_ID

    def test_get_returns_404_when_not_found(self, mock_context: MagicMock) -> None:
        event = _make_event("GET", f"/v1/memory/semantic/{_MEMORY_ID}")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = None

        with patch("lib.aurora.get_connection", return_value=mock_conn):
            with patch("lib.aurora.set_tenant_context"):
                result = handler(event, mock_context)

        assert result["statusCode"] == 404
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "NOT_FOUND"

    def test_get_includes_cors_headers(self, mock_context: MagicMock) -> None:
        result = self._run_get(mock_context)
        assert "Access-Control-Allow-Origin" in result["headers"]


# ---------------------------------------------------------------------------
# DELETE /v1/memory/semantic/{id}
# ---------------------------------------------------------------------------


class TestHandlerDelete:
    """Tests for DELETE /v1/memory/semantic/{id}."""

    def _run_delete(
        self,
        mock_context: MagicMock,
        memory_id: str = _MEMORY_ID,
        deleted_row: dict[str, Any] | None = None,
        tenant_id: str = _TENANT,
    ) -> dict[str, Any]:
        event = _make_event(
            "DELETE",
            f"/v1/memory/semantic/{memory_id}",
            tenant_id=tenant_id,
        )

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = deleted_row or {"id": memory_id}

        with patch("lib.aurora.get_connection", return_value=mock_conn):
            with patch("lib.aurora.set_tenant_context"):
                return handler(event, mock_context)

    def test_delete_returns_204_when_found(self, mock_context: MagicMock) -> None:
        result = self._run_delete(mock_context)
        assert result["statusCode"] == 204

    def test_delete_response_includes_request_id_in_meta(
        self, mock_context: MagicMock
    ) -> None:
        result = self._run_delete(mock_context)
        parsed = json.loads(result["body"])
        assert parsed["meta"]["request_id"] == _REQUEST_ID

    def test_delete_returns_404_when_not_found(self, mock_context: MagicMock) -> None:
        event = _make_event("DELETE", f"/v1/memory/semantic/{_MEMORY_ID}")

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor = MagicMock(return_value=mock_cursor)
        mock_cursor.fetchone.return_value = None

        with patch("lib.aurora.get_connection", return_value=mock_conn):
            with patch("lib.aurora.set_tenant_context"):
                result = handler(event, mock_context)

        assert result["statusCode"] == 404
        parsed = json.loads(result["body"])
        assert parsed["error"]["code"] == "NOT_FOUND"

    def test_delete_uses_authorizer_tenant(self, mock_context: MagicMock) -> None:
        result = self._run_delete(mock_context, tenant_id="secure-tenant")
        assert result["statusCode"] == 204

    def test_delete_response_has_cors_headers(self, mock_context: MagicMock) -> None:
        result = self._run_delete(mock_context)
        assert "Access-Control-Allow-Origin" in result["headers"]


# ---------------------------------------------------------------------------
# Models — SemanticCreateRequest, SemanticSearchRequest, SemanticResponse
# ---------------------------------------------------------------------------


class TestSemanticCreateRequest:
    """Unit tests for the SemanticCreateRequest Pydantic model."""

    def test_valid_request_parses(self) -> None:
        from lib.models import SemanticCreateRequest

        req = SemanticCreateRequest(agent_id=_AGENT, content="hello")
        assert req.agent_id == _AGENT
        assert req.content == "hello"
        assert req.namespace == "default"
        assert req.metadata == {}

    def test_custom_namespace_accepted(self) -> None:
        from lib.models import SemanticCreateRequest

        req = SemanticCreateRequest(agent_id=_AGENT, content="hello", namespace="facts")
        assert req.namespace == "facts"

    def test_metadata_accepted(self) -> None:
        from lib.models import SemanticCreateRequest

        req = SemanticCreateRequest(
            agent_id=_AGENT, content="hello", metadata={"source": "wiki"}
        )
        assert req.metadata == {"source": "wiki"}

    def test_missing_agent_id_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import SemanticCreateRequest

        with pytest.raises(ValidationError):
            SemanticCreateRequest(content="hello")  # type: ignore[call-arg]

    def test_missing_content_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import SemanticCreateRequest

        with pytest.raises(ValidationError):
            SemanticCreateRequest(agent_id=_AGENT)  # type: ignore[call-arg]

    def test_empty_content_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import SemanticCreateRequest

        with pytest.raises(ValidationError):
            SemanticCreateRequest(agent_id=_AGENT, content="")


class TestSemanticSearchRequest:
    """Unit tests for the SemanticSearchRequest Pydantic model."""

    def test_valid_request_parses(self) -> None:
        from lib.models import SemanticSearchRequest

        req = SemanticSearchRequest(query="what did the user say?")
        assert req.query == "what did the user say?"
        assert req.top_k == 10
        assert req.threshold == pytest.approx(0.7)
        assert req.agent_id is None
        assert req.namespace is None
        assert req.metadata_filter is None

    def test_top_k_boundary_min(self) -> None:
        from lib.models import SemanticSearchRequest

        req = SemanticSearchRequest(query="q", top_k=1)
        assert req.top_k == 1

    def test_top_k_boundary_max(self) -> None:
        from lib.models import SemanticSearchRequest

        req = SemanticSearchRequest(query="q", top_k=100)
        assert req.top_k == 100

    def test_top_k_above_max_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import SemanticSearchRequest

        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="q", top_k=101)

    def test_top_k_below_min_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import SemanticSearchRequest

        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="q", top_k=0)

    def test_threshold_boundary_zero(self) -> None:
        from lib.models import SemanticSearchRequest

        req = SemanticSearchRequest(query="q", threshold=0.0)
        assert req.threshold == pytest.approx(0.0)

    def test_threshold_boundary_one(self) -> None:
        from lib.models import SemanticSearchRequest

        req = SemanticSearchRequest(query="q", threshold=1.0)
        assert req.threshold == pytest.approx(1.0)

    def test_threshold_above_one_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import SemanticSearchRequest

        with pytest.raises(ValidationError):
            SemanticSearchRequest(query="q", threshold=1.1)

    def test_missing_query_raises(self) -> None:
        from pydantic import ValidationError

        from lib.models import SemanticSearchRequest

        with pytest.raises(ValidationError):
            SemanticSearchRequest()  # type: ignore[call-arg]

    def test_optional_fields_accepted(self) -> None:
        from lib.models import SemanticSearchRequest

        req = SemanticSearchRequest(
            query="q",
            agent_id=_AGENT,
            namespace="facts",
            metadata_filter={"source": "wiki"},
        )
        assert req.agent_id == _AGENT
        assert req.namespace == "facts"
        assert req.metadata_filter == {"source": "wiki"}


class TestSemanticResponse:
    """Unit tests for the SemanticResponse Pydantic model."""

    def test_valid_response_parses(self) -> None:
        from lib.models import SemanticResponse

        resp = SemanticResponse(
            id=_MEMORY_ID,
            agent_id=_AGENT,
            content="hello",
            namespace="default",
            metadata={},
            created_at=_NOW,
            updated_at=_NOW,
        )
        assert resp.id == _MEMORY_ID
        assert resp.similarity_score is None
        assert resp.deduplicated is False

    def test_similarity_score_and_deduplicated_set(self) -> None:
        from lib.models import SemanticResponse

        resp = SemanticResponse(
            id=_MEMORY_ID,
            agent_id=_AGENT,
            content="hello",
            namespace="default",
            metadata={},
            created_at=_NOW,
            updated_at=_NOW,
            similarity_score=0.92,
            deduplicated=True,
        )
        assert resp.similarity_score == pytest.approx(0.92)
        assert resp.deduplicated is True


# ---------------------------------------------------------------------------
# Embeddings module — unit tests
# ---------------------------------------------------------------------------


class TestGenerateEmbedding:
    """Unit tests for lib.embeddings.generate_embedding."""

    def test_returns_list_of_floats(self) -> None:
        from lib.embeddings import generate_embedding

        fake_response = {
            "body": MagicMock(
                read=lambda: json.dumps({"embedding": _FAKE_EMBEDDING}).encode()
            )
        }
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = fake_response

        with patch("lib.embeddings._get_client", return_value=mock_client):
            result = generate_embedding("hello world")

        assert isinstance(result, list)
        assert len(result) == 1024
        assert all(isinstance(v, float) for v in result)

    def test_calls_correct_model(self) -> None:
        from lib.embeddings import generate_embedding

        fake_response = {
            "body": MagicMock(
                read=lambda: json.dumps({"embedding": _FAKE_EMBEDDING}).encode()
            )
        }
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = fake_response

        with patch("lib.embeddings._get_client", return_value=mock_client):
            generate_embedding("test text")

        call_kwargs = mock_client.invoke_model.call_args
        assert call_kwargs.kwargs["modelId"] == "amazon.titan-embed-text-v2:0"

    def test_request_body_includes_dimensions_1024(self) -> None:
        from lib.embeddings import generate_embedding

        fake_response = {
            "body": MagicMock(
                read=lambda: json.dumps({"embedding": _FAKE_EMBEDDING}).encode()
            )
        }
        mock_client = MagicMock()
        mock_client.invoke_model.return_value = fake_response

        with patch("lib.embeddings._get_client", return_value=mock_client):
            generate_embedding("test text")

        sent_body = json.loads(mock_client.invoke_model.call_args.kwargs["body"])
        assert sent_body["dimensions"] == 1024
        assert sent_body["normalize"] is True

    def test_retries_on_throttling(self) -> None:
        from lib.embeddings import generate_embedding

        # Build a fake ClientError that looks throttled.
        class _FakeClientError(Exception):
            response = {"Error": {"Code": "ThrottlingException"}}

        fake_response = {
            "body": MagicMock(
                read=lambda: json.dumps({"embedding": _FAKE_EMBEDDING}).encode()
            )
        }
        mock_client = MagicMock()
        # Fail twice, succeed on third attempt.
        mock_client.invoke_model.side_effect = [
            _FakeClientError(),
            _FakeClientError(),
            fake_response,
        ]

        with patch("lib.embeddings._get_client", return_value=mock_client):
            with patch("lib.embeddings.time.sleep"):  # skip actual delays
                result = generate_embedding("retry me")

        assert mock_client.invoke_model.call_count == 3
        assert len(result) == 1024

    def test_raises_after_max_retries_exhausted(self) -> None:
        from lib.embeddings import generate_embedding

        class _FakeClientError(Exception):
            response = {"Error": {"Code": "ThrottlingException"}}

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = _FakeClientError()

        with patch("lib.embeddings._get_client", return_value=mock_client):
            with patch("lib.embeddings.time.sleep"):
                with pytest.raises(_FakeClientError):
                    generate_embedding("will fail")

        assert mock_client.invoke_model.call_count == 4  # 1 initial + 3 retries

    def test_non_retryable_error_raised_immediately(self) -> None:
        from lib.embeddings import generate_embedding

        mock_client = MagicMock()
        mock_client.invoke_model.side_effect = ValueError("bad input")

        with patch("lib.embeddings._get_client", return_value=mock_client):
            with pytest.raises(ValueError, match="bad input"):
                generate_embedding("fail immediately")

        # Should NOT retry on non-retryable errors.
        assert mock_client.invoke_model.call_count == 1


class TestGenerateEmbeddingsChunked:
    """Unit tests for lib.embeddings.generate_embeddings_chunked."""

    def test_short_text_returns_single_chunk(self) -> None:
        from lib.embeddings import generate_embeddings_chunked

        short_text = "This is a short sentence."

        with patch(
            "lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING
        ) as mock_embed:
            result = generate_embeddings_chunked(short_text)

        assert len(result) == 1
        assert result[0][0] == short_text
        mock_embed.assert_called_once_with(short_text)

    def test_long_text_returns_multiple_chunks(self) -> None:
        from lib.embeddings import generate_embeddings_chunked

        # 8001 tokens * 4 chars/token = 32004 chars — exceeds threshold.
        long_text = "x" * (8001 * 4)

        with patch(
            "lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING
        ) as mock_embed:
            result = generate_embeddings_chunked(long_text, chunk_size=512, overlap=50)

        assert len(result) > 1
        # Every element is (str, list).
        for chunk_text, embedding in result:
            assert isinstance(chunk_text, str)
            assert isinstance(embedding, list)
        # generate_embedding was called once per chunk.
        assert mock_embed.call_count == len(result)

    def test_all_chunks_covered_by_output(self) -> None:
        from lib.embeddings import generate_embeddings_chunked

        long_text = "a" * (8001 * 4)

        with patch("lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING):
            result = generate_embeddings_chunked(long_text, chunk_size=512, overlap=0)

        # Concatenation of non-overlapping chunks must cover the full text.
        reconstructed = "".join(chunk for chunk, _ in result)
        assert len(reconstructed) >= len(long_text)

    def test_chunked_text_at_exact_boundary(self) -> None:
        from lib.embeddings import generate_embeddings_chunked

        # Exactly at the threshold (8000 tokens * 4 = 32000 chars) → single chunk.
        boundary_text = "b" * (8000 * 4)

        with patch(
            "lib.embeddings.generate_embedding", return_value=_FAKE_EMBEDDING
        ) as mock_embed:
            result = generate_embeddings_chunked(boundary_text)

        assert len(result) == 1
        mock_embed.assert_called_once_with(boundary_text)
