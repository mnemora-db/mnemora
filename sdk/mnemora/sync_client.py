"""Synchronous wrapper around MnemoraClient.

For users who prefer synchronous code or are in environments where an
asyncio event loop is not already running (e.g. plain scripts, Jupyter
notebooks without nest_asyncio, CLI tools).

Internally spins up a dedicated asyncio event loop in the calling thread,
so it is NOT safe to call from an already-running event loop.  In async
contexts always use MnemoraClient directly.

Example::

    from mnemora import MnemoraSync

    # Context-manager form (recommended)
    with MnemoraSync(api_key="mnm_...") as client:
        state = client.get_state("agent-1")
        client.store_memory("agent-1", "The user prefers concise replies.")

    # Manual lifecycle
    client = MnemoraSync(api_key="mnm_...")
    client.store_state("agent-1", {"task": "write report"})
    client.close()
"""

from __future__ import annotations

import asyncio
from typing import Any

from mnemora.client import MnemoraClient
from mnemora.models import (
    EpisodeResponse,
    PurgeResponse,
    SearchResult,
    SemanticResponse,
    StateResponse,
    UsageResponse,
)


class MnemoraSync:
    """Synchronous wrapper around the async MnemoraClient.

    All public methods are thin ``run_until_complete`` shims that delegate
    to the corresponding coroutine on MnemoraClient.  Exceptions propagate
    unchanged — you get the same typed MnemoraError hierarchy.

    Parameters
    ----------
    api_key:
        Bearer token for authentication.
    base_url:
        Override the API root URL.  Falls back to ``MNEMORA_API_URL``
        env-var, then the production gateway.
    timeout:
        Per-request timeout in seconds.
    max_retries:
        Maximum retry attempts for 429 and 5xx responses.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        kwargs: dict[str, Any] = {
            "api_key": api_key,
            "timeout": timeout,
            "max_retries": max_retries,
        }
        if base_url is not None:
            kwargs["base_url"] = base_url

        self._async_client = MnemoraClient(**kwargs)
        self._loop = asyncio.new_event_loop()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> MnemoraSync:
        """Enter context manager, initialising the underlying async client."""
        self._loop.run_until_complete(self._async_client.__aenter__())
        return self

    def __exit__(self, *args: Any) -> None:
        """Exit context manager, closing HTTP connections and the event loop."""
        self._loop.run_until_complete(self._async_client.__aexit__(*args))
        self._loop.close()

    def close(self) -> None:
        """Close the HTTP client and shut down the internal event loop.

        Call this when not using the context-manager form.
        """
        self._loop.run_until_complete(self._async_client.close())
        self._loop.close()

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _run(self, coro: Any) -> Any:
        """Execute *coro* on the internal event loop and return its result."""
        return self._loop.run_until_complete(coro)

    # ------------------------------------------------------------------
    # Working memory
    # ------------------------------------------------------------------

    def store_state(
        self,
        agent_id: str,
        data: dict[str, Any],
        session_id: str | None = None,
        ttl_hours: int | None = None,
    ) -> StateResponse:
        """Synchronous wrapper for MnemoraClient.store_state.

        Args:
            agent_id: Identifier of the agent owning this state.
            data: Arbitrary JSON-serialisable key-value payload.
            session_id: Logical session label (defaults to "default").
            ttl_hours: How many hours to keep the record.

        Returns:
            The created or replaced StateResponse.
        """
        return self._run(
            self._async_client.store_state(agent_id, data, session_id, ttl_hours)
        )

    def get_state(
        self,
        agent_id: str,
        session_id: str | None = None,
    ) -> StateResponse:
        """Synchronous wrapper for MnemoraClient.get_state.

        Args:
            agent_id: Identifier of the agent.
            session_id: Restrict to a specific session.

        Returns:
            The current StateResponse for that agent.
        """
        return self._run(self._async_client.get_state(agent_id, session_id))

    def update_state(
        self,
        agent_id: str,
        data: dict[str, Any],
        version: int,
        session_id: str = "default",
        ttl_hours: int | None = None,
    ) -> StateResponse:
        """Synchronous wrapper for MnemoraClient.update_state.

        Args:
            agent_id: Identifier of the agent.
            data: New state payload.
            version: Expected current version for optimistic locking.
            session_id: Target session.
            ttl_hours: New TTL.

        Returns:
            The updated StateResponse.
        """
        return self._run(
            self._async_client.update_state(
                agent_id, data, version, session_id, ttl_hours
            )
        )

    def delete_state(self, agent_id: str, session_id: str) -> None:
        """Synchronous wrapper for MnemoraClient.delete_state.

        Args:
            agent_id: Identifier of the agent.
            session_id: Session to delete.
        """
        self._run(self._async_client.delete_state(agent_id, session_id))

    def list_sessions(self, agent_id: str) -> list[str]:
        """Synchronous wrapper for MnemoraClient.list_sessions.

        Args:
            agent_id: Identifier of the agent.

        Returns:
            List of session ID strings.
        """
        return self._run(self._async_client.list_sessions(agent_id))

    # ------------------------------------------------------------------
    # Semantic memory
    # ------------------------------------------------------------------

    def store_memory(
        self,
        agent_id: str,
        content: str,
        namespace: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SemanticResponse:
        """Synchronous wrapper for MnemoraClient.store_memory.

        Args:
            agent_id: Identifier of the agent.
            content: Text to embed and store.
            namespace: Logical partition within the agent.
            metadata: Arbitrary metadata to attach.

        Returns:
            The created or merged SemanticResponse.
        """
        return self._run(
            self._async_client.store_memory(agent_id, content, namespace, metadata)
        )

    def search_memory(
        self,
        query: str,
        agent_id: str | None = None,
        namespace: str | None = None,
        top_k: int = 10,
        threshold: float = 0.1,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[SemanticResponse]:
        """Synchronous wrapper for MnemoraClient.search_memory.

        Args:
            query: Natural-language search string.
            agent_id: Restrict results to a single agent.
            namespace: Restrict results to a namespace.
            top_k: Maximum number of results.
            threshold: Minimum cosine similarity threshold.
            metadata_filter: Metadata key-value filter.

        Returns:
            List of SemanticResponse objects sorted by similarity.
        """
        return self._run(
            self._async_client.search_memory(
                query, agent_id, namespace, top_k, threshold, metadata_filter
            )
        )

    def get_memory(self, memory_id: str) -> SemanticResponse:
        """Synchronous wrapper for MnemoraClient.get_memory.

        Args:
            memory_id: UUID of the semantic memory record.

        Returns:
            The SemanticResponse for that record.
        """
        return self._run(self._async_client.get_memory(memory_id))

    def delete_memory(self, memory_id: str) -> None:
        """Synchronous wrapper for MnemoraClient.delete_memory.

        Args:
            memory_id: UUID of the record to soft-delete.
        """
        self._run(self._async_client.delete_memory(memory_id))

    # ------------------------------------------------------------------
    # Episodic memory
    # ------------------------------------------------------------------

    def store_episode(
        self,
        agent_id: str,
        session_id: str,
        type: str,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> EpisodeResponse:
        """Synchronous wrapper for MnemoraClient.store_episode.

        Args:
            agent_id: Identifier of the agent.
            session_id: Session the episode belongs to.
            type: Event classification ("conversation", "action", etc.).
            content: Episode payload.
            metadata: Arbitrary metadata.

        Returns:
            The stored EpisodeResponse.
        """
        return self._run(
            self._async_client.store_episode(
                agent_id, session_id, type, content, metadata
            )
        )

    def get_episodes(
        self,
        agent_id: str,
        session_id: str | None = None,
        type: str | None = None,
        from_ts: str | None = None,
        to_ts: str | None = None,
        limit: int | None = None,
    ) -> list[EpisodeResponse]:
        """Synchronous wrapper for MnemoraClient.get_episodes.

        Args:
            agent_id: Identifier of the agent.
            session_id: Filter to a specific session.
            type: Filter to an event type.
            from_ts: ISO 8601 lower bound timestamp.
            to_ts: ISO 8601 upper bound timestamp.
            limit: Maximum number of episodes.

        Returns:
            List of EpisodeResponse objects in chronological order.
        """
        return self._run(
            self._async_client.get_episodes(
                agent_id, session_id, type, from_ts, to_ts, limit
            )
        )

    def get_session_episodes(
        self,
        agent_id: str,
        session_id: str,
    ) -> list[EpisodeResponse]:
        """Synchronous wrapper for MnemoraClient.get_session_episodes.

        Args:
            agent_id: Identifier of the agent.
            session_id: Session to replay.

        Returns:
            Ordered list of EpisodeResponse objects for that session.
        """
        return self._run(self._async_client.get_session_episodes(agent_id, session_id))

    # ------------------------------------------------------------------
    # Unified / cross-memory
    # ------------------------------------------------------------------

    def search_all(
        self,
        query: str,
        agent_id: str | None = None,
        top_k: int = 10,
    ) -> list[SearchResult]:
        """Synchronous wrapper for MnemoraClient.search_all.

        Args:
            query: Natural-language search string.
            agent_id: Restrict results to a single agent.
            top_k: Maximum number of results.

        Returns:
            Combined list of SearchResult objects.
        """
        return self._run(self._async_client.search_all(query, agent_id, top_k))

    def get_all_memory(self, agent_id: str) -> dict[str, Any]:
        """Synchronous wrapper for MnemoraClient.get_all_memory.

        Args:
            agent_id: Identifier of the agent.

        Returns:
            Combined dict with "state", "semantic", and "episodic" data.
        """
        return self._run(self._async_client.get_all_memory(agent_id))

    def purge_agent(self, agent_id: str) -> PurgeResponse:
        """Synchronous wrapper for MnemoraClient.purge_agent.

        Args:
            agent_id: Identifier of the agent to purge.

        Returns:
            PurgeResponse with deletion counts per tier.
        """
        return self._run(self._async_client.purge_agent(agent_id))

    # ------------------------------------------------------------------
    # Usage
    # ------------------------------------------------------------------

    def get_usage(self) -> UsageResponse:
        """Synchronous wrapper for MnemoraClient.get_usage.

        Returns:
            UsageResponse with billing-period metrics.
        """
        return self._run(self._async_client.get_usage())
