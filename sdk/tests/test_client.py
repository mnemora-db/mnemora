"""Tests for MnemoraClient (async) and MnemoraSync (sync wrapper).

All tests use httpx.MockTransport to intercept HTTP calls — no live server
required.  The mock handler mirrors the API response contract documented in
CLAUDE.md:

  success: { "data": {...}, "meta": { "request_id": "...", "latency_ms": N } }
  error:   { "error": { "code": "...", "message": "..." }, "meta": {...} }
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import pytest_asyncio

from mnemora import (
    MnemoraAuthError,
    MnemoraClient,
    MnemoraConflictError,
    MnemoraError,
    MnemoraNotFoundError,
    MnemoraRateLimitError,
    MnemoraSync,
    MnemoraValidationError,
)
from mnemora.models import (
    EpisodeResponse,
    PurgeResponse,
    SearchResult,
    SemanticResponse,
    StateResponse,
    UsageResponse,
)

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_BASE_URL = "http://test.mnemora"

_STATE = {
    "agent_id": "agent-1",
    "session_id": "default",
    "data": {"task": "summarize"},
    "version": 1,
    "created_at": "2026-03-01T00:00:00Z",
    "updated_at": "2026-03-01T00:00:00Z",
    "expires_at": None,
}

_STATE_V2 = {**_STATE, "version": 2, "data": {"task": "updated"}}

_SEMANTIC = {
    "id": "mem-uuid-1",
    "agent_id": "agent-1",
    "content": "The user prefers terse answers.",
    "namespace": "default",
    "metadata": {"source": "user"},
    "similarity_score": None,
    "created_at": "2026-03-01T00:00:00Z",
    "updated_at": "2026-03-01T00:00:00Z",
    "deduplicated": False,
}

_SEMANTIC_SEARCH_HIT = {**_SEMANTIC, "similarity_score": 0.92}

_EPISODE = {
    "id": "ep-uuid-1",
    "agent_id": "agent-1",
    "session_id": "sess-abc",
    "type": "conversation",
    "content": "Hello, world!",
    "metadata": {},
    "timestamp": "2026-03-01T10:00:00Z",
}

_USAGE = {
    "api_calls_month": 1000,
    "embeddings_generated_month": 50,
    "storage": {"dynamo_bytes": 2048, "s3_bytes": 4096},
    "agents_count": 3,
    "sessions_count": 12,
    "billing_period": "2026-03",
}

_PURGE = {
    "agent_id": "agent-1",
    "deleted": {"state": 2, "semantic": 45, "episodic": 120, "s3_objects": 3},
}


def _ok(data: Any) -> httpx.Response:
    """Build a 200 success response with the standard envelope."""
    return httpx.Response(
        200,
        json={"data": data, "meta": {"request_id": "req-test", "latency_ms": 5}},
    )


def _created(data: Any) -> httpx.Response:
    """Build a 201 created response."""
    return httpx.Response(
        201,
        json={"data": data, "meta": {"request_id": "req-test", "latency_ms": 8}},
    )


def _no_content() -> httpx.Response:
    """Build a 204 no-content response (empty body)."""
    return httpx.Response(204, content=b"")


def _err(status: int, code: str, message: str) -> httpx.Response:
    """Build an error response with the standard envelope."""
    return httpx.Response(
        status,
        json={
            "error": {"code": code, "message": message},
            "meta": {"request_id": "req-test", "latency_ms": 2},
        },
    )


def _mock_handler(request: httpx.Request) -> httpx.Response:
    """Central mock router — maps (method, path) to canned responses."""
    method = request.method
    path = request.url.path

    # ---- Working memory ----
    if method == "POST" and path == "/v1/state":
        return _ok(_STATE)

    if method == "GET" and path == "/v1/state/agent-1":
        return _ok(_STATE)

    if method == "GET" and path == "/v1/state/agent-missing":
        return _err(404, "NOT_FOUND", "Agent not found.")

    if method == "GET" and path == "/v1/state/agent-1/sessions":
        return _ok({"sessions": ["default", "sess-abc"]})

    if method == "PUT" and path == "/v1/state/agent-1":
        body = json.loads(request.content)
        if body.get("version") == 99:  # simulate version conflict
            return _err(409, "CONFLICT", "Version conflict.")
        return _ok(_STATE_V2)

    if method == "DELETE" and path == "/v1/state/agent-1/default":
        return _no_content()

    # ---- Semantic memory ----
    if method == "POST" and path == "/v1/memory/semantic":
        return _ok(_SEMANTIC)

    if method == "POST" and path == "/v1/memory/semantic/search":
        return _ok({"results": [_SEMANTIC_SEARCH_HIT]})

    if method == "GET" and path == "/v1/memory/semantic/mem-uuid-1":
        return _ok(_SEMANTIC)

    if method == "GET" and path == "/v1/memory/semantic/mem-missing":
        return _err(404, "NOT_FOUND", "Memory record not found.")

    if method == "DELETE" and path == "/v1/memory/semantic/mem-uuid-1":
        return _no_content()

    # ---- Episodic memory ----
    if method == "POST" and path == "/v1/memory/episodic":
        return _ok(_EPISODE)

    if method == "GET" and path == "/v1/memory/episodic/agent-1":
        return _ok({"episodes": [_EPISODE]})

    if method == "GET" and path == "/v1/memory/episodic/agent-1/sessions/sess-abc":
        return _ok({"episodes": [_EPISODE]})

    # ---- Unified ----
    if method == "POST" and path == "/v1/memory/search":
        return _ok(
            {
                "results": [
                    {
                        "memory_type": "semantic",
                        "id": "mem-uuid-1",
                        "agent_id": "agent-1",
                        "content": "The user prefers terse answers.",
                        "similarity_score": 0.88,
                        "metadata": {},
                        "created_at": "2026-03-01T00:00:00Z",
                    }
                ]
            }
        )

    if method == "GET" and path == "/v1/memory/agent-1":
        return _ok({"state": _STATE, "semantic": [], "episodic": []})

    if method == "DELETE" and path == "/v1/memory/agent-1":
        return _ok(_PURGE)

    # ---- Usage ----
    if method == "GET" and path == "/v1/usage":
        return _ok(_USAGE)

    # ---- Error triggers (used in error-handling tests) ----
    if path == "/v1/state/trigger-401":
        return _err(401, "UNAUTHORIZED", "Invalid API key.")
    if path == "/v1/state/trigger-400":
        return _err(400, "VALIDATION_ERROR", "agent_id is required.")
    if path == "/v1/state/trigger-429":
        return _err(429, "RATE_LIMITED", "Too many requests.")
    if path == "/v1/state/trigger-500":
        return _err(500, "INTERNAL_ERROR", "Internal server error.")

    # Default 404
    return _err(404, "NOT_FOUND", f"No route for {method} {path}")


def _make_async_client(transport: httpx.MockTransport | None = None) -> MnemoraClient:
    """Create a MnemoraClient wired to the mock transport."""
    transport = transport or httpx.MockTransport(_mock_handler)
    client = MnemoraClient(api_key="test-key", base_url=_BASE_URL)
    # Replace the internal httpx client with one backed by the mock transport
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url=_BASE_URL,
        headers={
            "Authorization": "Bearer test-key",
            "Content-Type": "application/json",
            "User-Agent": "mnemora-sdk/0.1.0",
        },
    )
    return client


@pytest_asyncio.fixture
async def client() -> MnemoraClient:
    """Async fixture: yields a MnemoraClient backed by the mock transport."""
    c = _make_async_client()
    yield c
    await c.close()


# ---------------------------------------------------------------------------
# 1. Construction & context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_async_context_manager() -> None:
    """Client must support `async with` and close cleanly."""
    c = _make_async_client()
    async with c:
        assert c.base_url == _BASE_URL


@pytest.mark.asyncio
async def test_default_base_url_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """MNEMORA_API_URL env var is honoured when no base_url is passed."""
    monkeypatch.setenv("MNEMORA_API_URL", "https://custom.api.example.com")
    c = MnemoraClient(api_key="key")
    assert c.base_url == "https://custom.api.example.com"
    await c.close()


@pytest.mark.asyncio
async def test_base_url_param_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit base_url constructor param takes precedence over env var."""
    monkeypatch.setenv("MNEMORA_API_URL", "https://env.example.com")
    c = MnemoraClient(api_key="key", base_url="https://explicit.example.com")
    assert c.base_url == "https://explicit.example.com"
    await c.close()


@pytest.mark.asyncio
async def test_auth_header_is_sent(client: MnemoraClient) -> None:
    """Authorization header must be present in every outbound request."""
    captured: list[httpx.Request] = []

    def capturing_handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok(_STATE)

    c = _make_async_client(httpx.MockTransport(capturing_handler))
    async with c:
        await c.get_state("agent-1")

    assert len(captured) == 1
    assert captured[0].headers["Authorization"] == "Bearer test-key"


@pytest.mark.asyncio
async def test_user_agent_header(client: MnemoraClient) -> None:
    """User-Agent header must identify the SDK and version."""
    captured: list[httpx.Request] = []

    def capturing_handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok(_STATE)

    c = _make_async_client(httpx.MockTransport(capturing_handler))
    async with c:
        await c.get_state("agent-1")

    assert "mnemora-sdk/" in captured[0].headers["User-Agent"]


# ---------------------------------------------------------------------------
# 2. Working memory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_state(client: MnemoraClient) -> None:
    result = await client.store_state("agent-1", {"task": "summarize"})
    assert isinstance(result, StateResponse)
    assert result.agent_id == "agent-1"
    assert result.session_id == "default"
    assert result.data == {"task": "summarize"}
    assert result.version == 1


@pytest.mark.asyncio
async def test_store_state_with_session_and_ttl(client: MnemoraClient) -> None:
    """store_state sends session_id and ttl_hours when provided."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok(_STATE)

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        await c.store_state("agent-1", {"k": "v"}, session_id="sess-x", ttl_hours=24)

    body = json.loads(captured[0].content)
    assert body["session_id"] == "sess-x"
    assert body["ttl_hours"] == 24


@pytest.mark.asyncio
async def test_get_state(client: MnemoraClient) -> None:
    result = await client.get_state("agent-1")
    assert isinstance(result, StateResponse)
    assert result.agent_id == "agent-1"


@pytest.mark.asyncio
async def test_get_state_with_session_id() -> None:
    """session_id is forwarded as a query parameter."""
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok(_STATE)

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        await c.get_state("agent-1", session_id="sess-abc")

    assert captured[0].url.params.get("session_id") == "sess-abc"


@pytest.mark.asyncio
async def test_update_state(client: MnemoraClient) -> None:
    result = await client.update_state("agent-1", {"task": "updated"}, version=1)
    assert isinstance(result, StateResponse)
    assert result.version == 2
    assert result.data == {"task": "updated"}


@pytest.mark.asyncio
async def test_update_state_sends_version_in_body() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok(_STATE_V2)

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        await c.update_state("agent-1", {"k": "v"}, version=7)

    body = json.loads(captured[0].content)
    assert body["version"] == 7


@pytest.mark.asyncio
async def test_delete_state(client: MnemoraClient) -> None:
    # Must not raise; 204 response returns None
    await client.delete_state("agent-1", "default")


@pytest.mark.asyncio
async def test_list_sessions(client: MnemoraClient) -> None:
    sessions = await client.list_sessions("agent-1")
    assert isinstance(sessions, list)
    assert "default" in sessions
    assert "sess-abc" in sessions


# ---------------------------------------------------------------------------
# 3. Semantic memory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_memory(client: MnemoraClient) -> None:
    result = await client.store_memory("agent-1", "The user prefers terse answers.")
    assert isinstance(result, SemanticResponse)
    assert result.id == "mem-uuid-1"
    assert result.content == "The user prefers terse answers."
    assert result.deduplicated is False


@pytest.mark.asyncio
async def test_store_memory_with_namespace_and_metadata() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok(_SEMANTIC)

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        await c.store_memory(
            "agent-1",
            "content",
            namespace="facts",
            metadata={"source": "user"},
        )

    body = json.loads(captured[0].content)
    assert body["namespace"] == "facts"
    assert body["metadata"] == {"source": "user"}


@pytest.mark.asyncio
async def test_search_memory(client: MnemoraClient) -> None:
    results = await client.search_memory("user preferences", agent_id="agent-1")
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], SemanticResponse)
    assert results[0].similarity_score == 0.92


@pytest.mark.asyncio
async def test_search_memory_sends_correct_body() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok({"results": []})

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        await c.search_memory(
            "query",
            agent_id="agent-1",
            namespace="ns",
            top_k=5,
            threshold=0.8,
            metadata_filter={"lang": "en"},
        )

    body = json.loads(captured[0].content)
    assert body["query"] == "query"
    assert body["agent_id"] == "agent-1"
    assert body["namespace"] == "ns"
    assert body["top_k"] == 5
    assert body["threshold"] == 0.8
    assert body["metadata_filter"] == {"lang": "en"}


@pytest.mark.asyncio
async def test_get_memory(client: MnemoraClient) -> None:
    result = await client.get_memory("mem-uuid-1")
    assert isinstance(result, SemanticResponse)
    assert result.id == "mem-uuid-1"


@pytest.mark.asyncio
async def test_delete_memory(client: MnemoraClient) -> None:
    await client.delete_memory("mem-uuid-1")  # must not raise


# ---------------------------------------------------------------------------
# 4. Episodic memory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_episode(client: MnemoraClient) -> None:
    result = await client.store_episode(
        agent_id="agent-1",
        session_id="sess-abc",
        type="conversation",
        content="Hello, world!",
    )
    assert isinstance(result, EpisodeResponse)
    assert result.id == "ep-uuid-1"
    assert result.type == "conversation"


@pytest.mark.asyncio
async def test_store_episode_sends_metadata() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok(_EPISODE)

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        await c.store_episode(
            "agent-1", "sess-abc", "action", "clicked button", metadata={"ui": "btn"}
        )

    body = json.loads(captured[0].content)
    assert body["metadata"] == {"ui": "btn"}


@pytest.mark.asyncio
async def test_get_episodes(client: MnemoraClient) -> None:
    episodes = await client.get_episodes("agent-1")
    assert isinstance(episodes, list)
    assert len(episodes) == 1
    assert isinstance(episodes[0], EpisodeResponse)


@pytest.mark.asyncio
async def test_get_episodes_forwards_filters() -> None:
    captured: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return _ok({"episodes": []})

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        await c.get_episodes(
            "agent-1",
            session_id="sess-abc",
            type="conversation",
            from_ts="2026-03-01T00:00:00Z",
            to_ts="2026-03-02T00:00:00Z",
            limit=50,
        )

    params = captured[0].url.params
    assert params.get("session_id") == "sess-abc"
    assert params.get("type") == "conversation"
    assert params.get("from") == "2026-03-01T00:00:00Z"
    assert params.get("to") == "2026-03-02T00:00:00Z"
    assert params.get("limit") == "50"


@pytest.mark.asyncio
async def test_get_session_episodes(client: MnemoraClient) -> None:
    episodes = await client.get_session_episodes("agent-1", "sess-abc")
    assert isinstance(episodes, list)
    assert len(episodes) == 1
    assert episodes[0].session_id == "sess-abc"


# ---------------------------------------------------------------------------
# 5. Unified / cross-memory
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_all(client: MnemoraClient) -> None:
    results = await client.search_all("user preferences", agent_id="agent-1")
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], SearchResult)
    assert results[0].memory_type == "semantic"
    assert results[0].similarity_score == 0.88


@pytest.mark.asyncio
async def test_get_all_memory(client: MnemoraClient) -> None:
    result = await client.get_all_memory("agent-1")
    assert isinstance(result, dict)
    assert "state" in result


@pytest.mark.asyncio
async def test_purge_agent(client: MnemoraClient) -> None:
    result = await client.purge_agent("agent-1")
    assert isinstance(result, PurgeResponse)
    assert result.agent_id == "agent-1"
    assert result.deleted["semantic"] == 45


# ---------------------------------------------------------------------------
# 6. Usage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_usage(client: MnemoraClient) -> None:
    result = await client.get_usage()
    assert isinstance(result, UsageResponse)
    assert result.api_calls_month == 1000
    assert result.billing_period == "2026-03"
    assert result.storage["dynamo_bytes"] == 2048


# ---------------------------------------------------------------------------
# 7. Error handling — each HTTP status maps to the right exception
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_401_raises_auth_error(client: MnemoraClient) -> None:
    with pytest.raises(MnemoraAuthError) as exc_info:
        await client.get_state("trigger-401")
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_404_raises_not_found(client: MnemoraClient) -> None:
    with pytest.raises(MnemoraNotFoundError) as exc_info:
        await client.get_state("agent-missing")
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_404_semantic_raises_not_found(client: MnemoraClient) -> None:
    with pytest.raises(MnemoraNotFoundError):
        await client.get_memory("mem-missing")


@pytest.mark.asyncio
async def test_409_raises_conflict_error(client: MnemoraClient) -> None:
    with pytest.raises(MnemoraConflictError) as exc_info:
        await client.update_state("agent-1", {}, version=99)
    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "CONFLICT"


@pytest.mark.asyncio
async def test_400_raises_validation_error(client: MnemoraClient) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _err(400, "VALIDATION_ERROR", "agent_id is required.")

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        with pytest.raises(MnemoraValidationError) as exc_info:
            await c.store_state("x", {})
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_500_raises_mnemora_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return _err(500, "INTERNAL_ERROR", "Internal server error.")

    c = _make_async_client(httpx.MockTransport(handler))
    async with c:
        with pytest.raises(MnemoraError) as exc_info:
            await c.get_state("agent-1")
    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_429_exhausts_retries_and_raises() -> None:
    """A persistent 429 should exhaust retries and raise MnemoraRateLimitError."""
    call_count = 0

    def always_429(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _err(429, "RATE_LIMITED", "Slow down.")

    # Use max_retries=2 to keep the test fast (3 total attempts)
    c = MnemoraClient(api_key="key", base_url=_BASE_URL, max_retries=2)
    c._client = httpx.AsyncClient(
        transport=httpx.MockTransport(always_429),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer key"},
    )

    # Patch asyncio.sleep so the test doesn't actually wait
    import asyncio
    from unittest.mock import AsyncMock, patch

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        async with c:
            with pytest.raises(MnemoraRateLimitError):
                await c.get_state("agent-1")

    # max_retries=2 means 3 attempts total (initial + 2 retries)
    assert call_count == 3


@pytest.mark.asyncio
async def test_5xx_retries_then_raises() -> None:
    """5xx errors should be retried up to max_retries times."""
    call_count = 0

    def always_500(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _err(500, "INTERNAL_ERROR", "Server exploded.")

    c = MnemoraClient(api_key="key", base_url=_BASE_URL, max_retries=1)
    c._client = httpx.AsyncClient(
        transport=httpx.MockTransport(always_500),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer key"},
    )

    import asyncio
    from unittest.mock import AsyncMock, patch

    with patch.object(asyncio, "sleep", new_callable=AsyncMock):
        async with c:
            with pytest.raises(MnemoraError) as exc_info:
                await c.get_state("agent-1")

    assert exc_info.value.status_code == 500
    # max_retries=1 => 2 total attempts
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_respects_retry_after_header() -> None:
    """Retry-After header value is incorporated into the back-off delay."""

    def handler(request: httpx.Request) -> httpx.Response:
        _err(429, "RATE_LIMITED", "Slow down.")
        # Return a mutable response with Retry-After header
        return httpx.Response(
            429,
            headers={"Retry-After": "3"},
            json={
                "error": {"code": "RATE_LIMITED", "message": "Slow down."},
                "meta": {},
            },
        )

    c = MnemoraClient(api_key="key", base_url=_BASE_URL, max_retries=1)
    c._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer key"},
    )

    import asyncio
    from unittest.mock import AsyncMock, patch

    mock_sleep = AsyncMock()
    with patch.object(asyncio, "sleep", mock_sleep):
        async with c:
            with pytest.raises(MnemoraRateLimitError):
                await c.get_state("agent-1")

    # The delay should have been at least 3 s (from Retry-After)
    assert mock_sleep.called
    actual_delay = mock_sleep.call_args_list[0][0][0]
    assert actual_delay >= 3.0


@pytest.mark.asyncio
async def test_4xx_no_retry() -> None:
    """4xx errors (except 429) must NOT be retried."""
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return _err(404, "NOT_FOUND", "Not found.")

    c = MnemoraClient(api_key="key", base_url=_BASE_URL, max_retries=3)
    c._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer key"},
    )
    async with c:
        with pytest.raises(MnemoraNotFoundError):
            await c.get_state("agent-1")

    assert call_count == 1


# ---------------------------------------------------------------------------
# 8. Exception class hierarchy and attributes
# ---------------------------------------------------------------------------


def test_exception_hierarchy() -> None:
    """All typed exceptions must be subclasses of MnemoraError."""
    assert issubclass(MnemoraAuthError, MnemoraError)
    assert issubclass(MnemoraNotFoundError, MnemoraError)
    assert issubclass(MnemoraConflictError, MnemoraError)
    assert issubclass(MnemoraRateLimitError, MnemoraError)
    assert issubclass(MnemoraValidationError, MnemoraError)


def test_exception_attributes() -> None:
    err = MnemoraError("oops", code="ERR", status_code=500)
    assert err.message == "oops"
    assert err.code == "ERR"
    assert err.status_code == 500
    assert str(err) == "oops"


def test_exception_defaults() -> None:
    assert MnemoraAuthError().status_code == 401
    assert MnemoraNotFoundError().status_code == 404
    assert MnemoraConflictError().status_code == 409
    assert MnemoraRateLimitError().status_code == 429
    assert MnemoraValidationError().status_code == 400


# ---------------------------------------------------------------------------
# 9. Pydantic models
# ---------------------------------------------------------------------------


def test_state_response_model() -> None:
    state = StateResponse(**_STATE)
    assert state.agent_id == "agent-1"
    assert state.version == 1
    assert state.expires_at is None


def test_state_response_extra_fields_allowed() -> None:
    """Forward-compatible: extra API fields must not cause a ValidationError."""
    state = StateResponse(**{**_STATE, "future_field": "x"})
    assert state.agent_id == "agent-1"


def test_semantic_response_model() -> None:
    sem = SemanticResponse(**_SEMANTIC)
    assert sem.id == "mem-uuid-1"
    assert sem.deduplicated is False
    assert sem.similarity_score is None


def test_episode_response_model() -> None:
    ep = EpisodeResponse(**_EPISODE)
    assert ep.id == "ep-uuid-1"
    assert ep.type == "conversation"


def test_purge_response_model() -> None:
    purge = PurgeResponse(**_PURGE)
    assert purge.agent_id == "agent-1"
    assert purge.deleted["s3_objects"] == 3


def test_usage_response_model() -> None:
    usage = UsageResponse(**_USAGE)
    assert usage.api_calls_month == 1000
    assert usage.billing_period == "2026-03"


def test_search_result_model() -> None:
    sr = SearchResult(memory_type="semantic", id="x", similarity_score=0.9)
    assert sr.memory_type == "semantic"
    assert sr.similarity_score == 0.9
    assert sr.relevance is None


# ---------------------------------------------------------------------------
# 10. Sync client
# ---------------------------------------------------------------------------


def test_sync_store_state() -> None:
    """MnemoraSync.store_state returns a StateResponse."""
    c = MnemoraSync(api_key="test-key", base_url=_BASE_URL)
    c._async_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer test-key"},
    )
    with c:
        result = c.store_state("agent-1", {"task": "summarize"})
    assert isinstance(result, StateResponse)
    assert result.agent_id == "agent-1"


def test_sync_get_state() -> None:
    c = MnemoraSync(api_key="test-key", base_url=_BASE_URL)
    c._async_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer test-key"},
    )
    with c:
        result = c.get_state("agent-1")
    assert isinstance(result, StateResponse)


def test_sync_search_memory() -> None:
    c = MnemoraSync(api_key="test-key", base_url=_BASE_URL)
    c._async_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer test-key"},
    )
    with c:
        results = c.search_memory("preferences", agent_id="agent-1")
    assert isinstance(results, list)
    assert len(results) == 1
    assert isinstance(results[0], SemanticResponse)


def test_sync_store_episode() -> None:
    c = MnemoraSync(api_key="test-key", base_url=_BASE_URL)
    c._async_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer test-key"},
    )
    with c:
        result = c.store_episode("agent-1", "sess-abc", "conversation", "Hello")
    assert isinstance(result, EpisodeResponse)


def test_sync_raises_typed_exception() -> None:
    """Typed exceptions propagate correctly through the sync wrapper."""
    c = MnemoraSync(api_key="test-key", base_url=_BASE_URL)
    c._async_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer test-key"},
    )
    with c, pytest.raises(MnemoraNotFoundError):
        c.get_state("agent-missing")


def test_sync_get_usage() -> None:
    c = MnemoraSync(api_key="test-key", base_url=_BASE_URL)
    c._async_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer test-key"},
    )
    with c:
        result = c.get_usage()
    assert isinstance(result, UsageResponse)
    assert result.api_calls_month == 1000


def test_sync_purge_agent() -> None:
    c = MnemoraSync(api_key="test-key", base_url=_BASE_URL)
    c._async_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(_mock_handler),
        base_url=_BASE_URL,
        headers={"Authorization": "Bearer test-key"},
    )
    with c:
        result = c.purge_agent("agent-1")
    assert isinstance(result, PurgeResponse)
    assert result.deleted["semantic"] == 45


# ---------------------------------------------------------------------------
# 11. Package-level imports from mnemora.__init__
# ---------------------------------------------------------------------------


def test_package_exports() -> None:
    import mnemora

    assert hasattr(mnemora, "MnemoraClient")
    assert hasattr(mnemora, "MnemoraSync")
    assert hasattr(mnemora, "MnemoraError")
    assert hasattr(mnemora, "MnemoraAuthError")
    assert hasattr(mnemora, "MnemoraNotFoundError")
    assert hasattr(mnemora, "MnemoraConflictError")
    assert hasattr(mnemora, "MnemoraRateLimitError")
    assert hasattr(mnemora, "MnemoraValidationError")
    assert hasattr(mnemora, "StateResponse")
    assert hasattr(mnemora, "SemanticResponse")
    assert hasattr(mnemora, "EpisodeResponse")
    assert hasattr(mnemora, "SearchResult")
    assert hasattr(mnemora, "PurgeResponse")
    assert hasattr(mnemora, "UsageResponse")
    assert mnemora.__version__ == "0.1.0"
