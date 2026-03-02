"""Async HTTP client for the Mnemora API.

This module exposes MnemoraClient — the primary entry-point for the SDK.
All network I/O is performed via httpx.AsyncClient, making the client
safe to use inside asyncio event loops (LangGraph, FastAPI, etc.).

Quick-start::

    import asyncio
    from mnemora import MnemoraClient

    async def main():
        async with MnemoraClient(api_key="mnm_...") as client:
            await client.store_state("agent-1", {"task": "summarize"})
            results = await client.search_memory("what was the last task?",
                                                 agent_id="agent-1")
            for r in results:
                print(r.content, r.similarity_score)

    asyncio.run(main())

Environment variables
---------------------
MNEMORA_API_URL
    Override the default base URL without changing code.  The constructor
    parameter ``base_url`` takes precedence over this variable.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
from typing import Any

import httpx

from mnemora.exceptions import (
    MnemoraAuthError,
    MnemoraConflictError,
    MnemoraError,
    MnemoraNotFoundError,
    MnemoraRateLimitError,
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

_SDK_VERSION = "0.1.0"
_DEFAULT_BASE_URL = "https://api.mnemora.dev"


class MnemoraClient:
    """Async client for the Mnemora memory API.

    Parameters
    ----------
    api_key:
        Bearer token for authentication.  Never logged or stored beyond
        the ``Authorization`` request header.
    base_url:
        Root URL of the Mnemora API, without a trailing slash.  Falls
        back to the ``MNEMORA_API_URL`` environment variable, then to
        the production gateway URL.
    timeout:
        Per-request timeout in seconds passed to httpx.
    max_retries:
        Maximum number of retry attempts for 429 and 5xx responses.
        Retries use exponential back-off (0.5 s, 1 s, 2 s, …).

    Example::

        # As an async context manager (recommended)
        async with MnemoraClient(api_key="mnm_...") as client:
            state = await client.get_state("my-agent")

        # Manual lifecycle management
        client = MnemoraClient(api_key="mnm_...")
        state = await client.get_state("my-agent")
        await client.close()
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        resolved_url = (
            base_url or os.environ.get("MNEMORA_API_URL") or _DEFAULT_BASE_URL
        ).rstrip("/")

        self.base_url = resolved_url
        self.max_retries = max_retries

        self._client = httpx.AsyncClient(
            base_url=resolved_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": f"mnemora-sdk/{_SDK_VERSION}",
            },
            timeout=httpx.Timeout(timeout),
        )

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> MnemoraClient:
        """Enter the async context manager, returning self."""
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit the async context manager and close the underlying HTTP client."""
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx.AsyncClient and release connections."""
        await self._client.aclose()

    # ------------------------------------------------------------------
    # Internal request helper
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Send an HTTP request with automatic retry on transient errors.

        Retries 429 and 5xx responses up to ``self.max_retries`` times with
        exponential back-off.  Respects the ``Retry-After`` response header
        when present.

        Args:
            method: HTTP method ("GET", "POST", "PUT", "DELETE", …).
            path: URL path, e.g. "/v1/state/agent-1".
            **kwargs: Extra keyword arguments forwarded to httpx's request
                method (e.g. ``json=``, ``params=``).

        Returns:
            The ``data`` value from the JSON response body.

        Raises:
            MnemoraAuthError: API responded with 401.
            MnemoraNotFoundError: API responded with 404.
            MnemoraConflictError: API responded with 409.
            MnemoraRateLimitError: 429 persisted after all retries.
            MnemoraValidationError: API responded with 400.
            MnemoraError: Any other non-2xx status code.
        """
        last_response: httpx.Response | None = None

        for attempt in range(self.max_retries + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
            except httpx.TimeoutException as exc:
                raise MnemoraError(
                    f"Request timed out: {exc}",
                    code="TIMEOUT",
                    status_code=0,
                ) from exc
            except httpx.RequestError as exc:
                raise MnemoraError(
                    f"Network error: {exc}",
                    code="NETWORK_ERROR",
                    status_code=0,
                ) from exc

            last_response = response

            # Transient errors eligible for retry
            is_transient = response.status_code == 429 or response.status_code >= 500
            if is_transient and attempt < self.max_retries:
                delay = (2**attempt) * 0.5  # 0.5 s, 1 s, 2 s
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    with contextlib.suppress(ValueError):
                        delay = max(delay, float(retry_after))
                await asyncio.sleep(delay)
                continue

            break

        assert last_response is not None  # loop always executes at least once

        # Successful response
        if last_response.status_code < 400:
            # 204 No Content — no body to parse, return None
            if last_response.status_code == 204 or not last_response.content:
                return None
            try:
                payload = last_response.json()
            except Exception as exc:
                raise MnemoraError(
                    "Server returned non-JSON response.",
                    code="PARSE_ERROR",
                    status_code=last_response.status_code,
                ) from exc
            return payload.get("data", payload)

        # Error response — parse and raise
        try:
            error_body = last_response.json()
        except Exception:
            error_body = {}

        self._raise_for_status(last_response.status_code, error_body)

    def _raise_for_status(self, status_code: int, data: dict[str, Any]) -> None:
        """Convert an error response into the appropriate typed exception.

        Args:
            status_code: HTTP status code of the error response.
            data: Parsed JSON response body.

        Raises:
            MnemoraAuthError: For 401 responses.
            MnemoraNotFoundError: For 404 responses.
            MnemoraConflictError: For 409 responses.
            MnemoraRateLimitError: For 429 responses.
            MnemoraValidationError: For 400 responses.
            MnemoraError: For all other non-2xx responses.
        """
        error = data.get("error", {})
        message: str = error.get("message", "Unknown error")
        code: str = error.get("code", "UNKNOWN")

        if status_code == 401:
            raise MnemoraAuthError(message, code=code)
        if status_code == 404:
            raise MnemoraNotFoundError(message, code=code)
        if status_code == 409:
            raise MnemoraConflictError(message, code=code)
        if status_code == 429:
            raise MnemoraRateLimitError(message, code=code)
        if status_code == 400:
            raise MnemoraValidationError(message, code=code)
        raise MnemoraError(message, code=code, status_code=status_code)

    # ------------------------------------------------------------------
    # Working memory (DynamoDB state)
    # ------------------------------------------------------------------

    async def store_state(
        self,
        agent_id: str,
        data: dict[str, Any],
        session_id: str | None = None,
        ttl_hours: int | None = None,
    ) -> StateResponse:
        """Store or overwrite an agent's working-memory state.

        Args:
            agent_id: Identifier of the agent owning this state.
            data: Arbitrary JSON-serialisable key-value payload to store.
            session_id: Logical session label (defaults to "default" server-side).
            ttl_hours: How many hours to keep the record.  Omit for no expiry.

        Returns:
            The created or replaced StateResponse record.

        Raises:
            MnemoraValidationError: If the payload fails server validation.
            MnemoraAuthError: If authentication fails.
        """
        body: dict[str, Any] = {"agent_id": agent_id, "data": data}
        if session_id is not None:
            body["session_id"] = session_id
        if ttl_hours is not None:
            body["ttl_hours"] = ttl_hours
        result = await self._request("POST", "/v1/state", json=body)
        return StateResponse(**result)

    async def get_state(
        self,
        agent_id: str,
        session_id: str | None = None,
    ) -> StateResponse:
        """Retrieve the current state for an agent.

        Args:
            agent_id: Identifier of the agent.
            session_id: Restrict to a specific session.  Omit for the default.

        Returns:
            The latest StateResponse for that agent (and session).

        Raises:
            MnemoraNotFoundError: If no state exists for the given agent.
            MnemoraAuthError: If authentication fails.
        """
        params: dict[str, str] = {}
        if session_id is not None:
            params["session_id"] = session_id
        result = await self._request(
            "GET", f"/v1/state/{agent_id}", params=params or None
        )
        return StateResponse(**result)

    async def update_state(
        self,
        agent_id: str,
        data: dict[str, Any],
        version: int,
        session_id: str = "default",
        ttl_hours: int | None = None,
    ) -> StateResponse:
        """Update an agent's state with optimistic locking.

        Pass the ``version`` value returned by a prior get_state() or
        store_state() call.  The server will reject the update with a
        MnemoraConflictError if the record has been modified concurrently.

        Args:
            agent_id: Identifier of the agent.
            data: New state payload (replaces existing data).
            version: Expected current version for optimistic locking.
            session_id: Target session (defaults to "default").
            ttl_hours: New TTL.  Omit to keep the existing TTL.

        Returns:
            The updated StateResponse with an incremented version number.

        Raises:
            MnemoraConflictError: If the server-side version does not match.
            MnemoraNotFoundError: If the agent / session does not exist.
            MnemoraAuthError: If authentication fails.
        """
        body: dict[str, Any] = {
            "data": data,
            "version": version,
            "session_id": session_id,
        }
        if ttl_hours is not None:
            body["ttl_hours"] = ttl_hours
        result = await self._request("PUT", f"/v1/state/{agent_id}", json=body)
        return StateResponse(**result)

    async def delete_state(self, agent_id: str, session_id: str) -> None:
        """Delete a specific session's state record.

        Args:
            agent_id: Identifier of the agent.
            session_id: Session to delete.

        Returns:
            None on success (HTTP 204).

        Raises:
            MnemoraNotFoundError: If the session does not exist.
            MnemoraAuthError: If authentication fails.
        """
        await self._request("DELETE", f"/v1/state/{agent_id}/{session_id}")

    async def list_sessions(self, agent_id: str) -> list[str]:
        """List all session IDs for an agent.

        Args:
            agent_id: Identifier of the agent.

        Returns:
            A list of session ID strings (may be empty).

        Raises:
            MnemoraAuthError: If authentication fails.
        """
        result = await self._request("GET", f"/v1/state/{agent_id}/sessions")
        if isinstance(result, dict):
            return result.get("sessions", [])
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Semantic memory (Aurora pgvector)
    # ------------------------------------------------------------------

    async def store_memory(
        self,
        agent_id: str,
        content: str,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SemanticResponse:
        """Store a text snippet as a semantic memory entry.

        The API server automatically generates a 1024-dimensional Bedrock
        Titan embedding.  Duplicate content (cosine similarity > 0.95) is
        merged rather than re-inserted.

        Args:
            agent_id: Identifier of the agent owning this memory.
            content: Natural-language text to embed and store.
            namespace: Logical partition within the agent (default "default").
            metadata: Arbitrary JSON-serialisable metadata to attach.

        Returns:
            The created or merged SemanticResponse, with ``deduplicated=True``
            if an existing record was updated.

        Raises:
            MnemoraValidationError: If the payload fails server validation.
            MnemoraAuthError: If authentication fails.
        """
        body: dict[str, Any] = {"agent_id": agent_id, "content": content}
        if namespace is not None:
            body["namespace"] = namespace
        if metadata is not None:
            body["metadata"] = metadata
        result = await self._request("POST", "/v1/memory/semantic", json=body)
        return SemanticResponse(**result)

    async def search_memory(
        self,
        query: str,
        agent_id: str | None = None,
        namespace: str | None = None,
        top_k: int = 10,
        threshold: float = 0.7,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SemanticResponse]:
        """Search semantic memory by natural-language query.

        The API embeds the query with Bedrock Titan and returns the
        most-similar records above the similarity threshold.

        Args:
            query: Natural-language search string.
            agent_id: Restrict results to a single agent.  Omit for
                tenant-wide search.
            namespace: Restrict results to a logical namespace.
            top_k: Maximum number of results to return.
            threshold: Minimum cosine similarity (0–1) for inclusion.
            metadata_filter: Key-value pairs that must match the record
                ``metadata`` field (exact match per key).

        Returns:
            List of SemanticResponse objects sorted by similarity (highest
            first).  May be empty.

        Raises:
            MnemoraAuthError: If authentication fails.
        """
        body: dict[str, Any] = {
            "query": query,
            "top_k": top_k,
            "threshold": threshold,
        }
        if agent_id is not None:
            body["agent_id"] = agent_id
        if namespace is not None:
            body["namespace"] = namespace
        if metadata_filter is not None:
            body["metadata_filter"] = metadata_filter
        result = await self._request("POST", "/v1/memory/semantic/search", json=body)
        if isinstance(result, dict):
            items = result.get("results", [])
        elif isinstance(result, list):
            items = result
        else:
            items = []
        return [SemanticResponse(**r) for r in items]

    async def get_memory(self, memory_id: str) -> SemanticResponse:
        """Retrieve a semantic memory record by its UUID.

        Args:
            memory_id: UUID of the semantic memory record.

        Returns:
            The SemanticResponse for that record.

        Raises:
            MnemoraNotFoundError: If the record does not exist or has been
                soft-deleted.
            MnemoraAuthError: If authentication fails.
        """
        result = await self._request("GET", f"/v1/memory/semantic/{memory_id}")
        return SemanticResponse(**result)

    async def delete_memory(self, memory_id: str) -> None:
        """Soft-delete a semantic memory record (sets valid_until to now).

        Args:
            memory_id: UUID of the semantic memory record to delete.

        Returns:
            None on success.

        Raises:
            MnemoraNotFoundError: If the record does not exist.
            MnemoraAuthError: If authentication fails.
        """
        await self._request("DELETE", f"/v1/memory/semantic/{memory_id}")

    # ------------------------------------------------------------------
    # Episodic memory (DynamoDB hot + S3 cold)
    # ------------------------------------------------------------------

    async def store_episode(
        self,
        agent_id: str,
        session_id: str,
        type: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodeResponse:
        """Append a time-stamped episode to episodic memory.

        Args:
            agent_id: Identifier of the agent that produced the episode.
            session_id: Session the episode belongs to.
            type: Event classification.  Must be one of: "conversation",
                "action", "observation", "tool_call".
            content: Episode payload — plain text or a JSON-serialisable object.
            metadata: Arbitrary metadata to attach to the episode.

        Returns:
            The stored EpisodeResponse.

        Raises:
            MnemoraValidationError: If ``type`` is not a recognised value.
            MnemoraAuthError: If authentication fails.
        """
        body: dict[str, Any] = {
            "agent_id": agent_id,
            "session_id": session_id,
            "type": type,
            "content": content,
        }
        if metadata is not None:
            body["metadata"] = metadata
        result = await self._request("POST", "/v1/memory/episodic", json=body)
        return EpisodeResponse(**result)

    async def get_episodes(
        self,
        agent_id: str,
        session_id: str | None = None,
        type: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        limit: int | None = None,
    ) -> list[EpisodeResponse]:
        """Query episodic memory with optional time-range and type filters.

        Args:
            agent_id: Identifier of the agent.
            session_id: Filter to a specific session.
            type: Filter to an event type ("conversation", "action", etc.).
            from_ts: ISO 8601 lower bound for the episode timestamp (inclusive).
            to_ts: ISO 8601 upper bound for the episode timestamp (inclusive).
            limit: Maximum number of episodes to return.

        Returns:
            List of EpisodeResponse objects in chronological order.

        Raises:
            MnemoraAuthError: If authentication fails.
        """
        params: dict[str, str] = {}
        if session_id is not None:
            params["session_id"] = session_id
        if type is not None:
            params["type"] = type
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        if limit is not None:
            params["limit"] = str(limit)
        result = await self._request(
            "GET",
            f"/v1/memory/episodic/{agent_id}",
            params=params or None,
        )
        if isinstance(result, dict):
            items = result.get("episodes", [])
        elif isinstance(result, list):
            items = result
        else:
            items = []
        return [EpisodeResponse(**ep) for ep in items]

    async def get_session_episodes(
        self,
        agent_id: str,
        session_id: str,
    ) -> list[EpisodeResponse]:
        """Replay all episodes for a specific session in chronological order.

        Args:
            agent_id: Identifier of the agent.
            session_id: Session to replay.

        Returns:
            Ordered list of EpisodeResponse objects for that session.

        Raises:
            MnemoraNotFoundError: If the session does not exist.
            MnemoraAuthError: If authentication fails.
        """
        result = await self._request(
            "GET",
            f"/v1/memory/episodic/{agent_id}/sessions/{session_id}",
        )
        if isinstance(result, dict):
            items = result.get("episodes", [])
        elif isinstance(result, list):
            items = result
        else:
            items = []
        return [EpisodeResponse(**ep) for ep in items]

    # ------------------------------------------------------------------
    # Unified / cross-memory operations
    # ------------------------------------------------------------------

    async def search_all(
        self,
        query: str,
        agent_id: str | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Search across all memory types simultaneously.

        Args:
            query: Natural-language search string.
            agent_id: Restrict results to a single agent.
            top_k: Maximum number of combined results.

        Returns:
            List of SearchResult objects from both semantic and episodic
            memory, sorted by relevance.

        Raises:
            MnemoraAuthError: If authentication fails.
        """
        body: dict[str, Any] = {"query": query, "top_k": top_k}
        if agent_id is not None:
            body["agent_id"] = agent_id
        result = await self._request("POST", "/v1/memory/search", json=body)
        if isinstance(result, dict):
            items = result.get("results", [])
        elif isinstance(result, list):
            items = result
        else:
            items = []
        return [SearchResult(**r) for r in items]

    async def get_all_memory(self, agent_id: str) -> dict[str, Any]:
        """Retrieve a combined view of all memory types for an agent.

        Args:
            agent_id: Identifier of the agent.

        Returns:
            Raw response dict containing "state", "semantic", and "episodic"
            sub-objects.  Kept as a raw dict because the unified shape is
            heterogeneous.

        Raises:
            MnemoraAuthError: If authentication fails.
        """
        result = await self._request("GET", f"/v1/memory/{agent_id}")
        return result if isinstance(result, dict) else {"raw": result}

    async def purge_agent(self, agent_id: str) -> PurgeResponse:
        """Permanently delete all data for an agent (GDPR purge).

        Removes state, semantic memories, episodic records, and S3 objects
        for the given agent.  This operation is irreversible.

        Args:
            agent_id: Identifier of the agent to purge.

        Returns:
            PurgeResponse with record counts per deleted tier.

        Raises:
            MnemoraAuthError: If authentication fails.
        """
        result = await self._request("DELETE", f"/v1/memory/{agent_id}")
        return PurgeResponse(**result)

    # ------------------------------------------------------------------
    # Usage / billing
    # ------------------------------------------------------------------

    async def get_usage(self) -> UsageResponse:
        """Retrieve current billing-period usage metrics.

        Returns:
            UsageResponse with API call counts, embedding counts, storage
            bytes, and the billing period label.

        Raises:
            MnemoraAuthError: If authentication fails.
        """
        result = await self._request("GET", "/v1/usage")
        return UsageResponse(**result)
