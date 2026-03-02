"""LangGraph CheckpointSaver backed by Mnemora.

Uses Mnemora's working-memory (state) API to persist LangGraph graph state
across invocations.  Each ``thread_id`` maps to a Mnemora ``agent_id``; the
checkpoint namespace maps to a ``session_id`` so the same thread can hold
multiple named checkpoint streams.

Usage::

    from mnemora import MnemoraClient
    from mnemora.integrations.langgraph import MnemoraCheckpointSaver

    client = MnemoraClient(api_key="mnm_...")
    saver = MnemoraCheckpointSaver(client=client)

    # Use with LangGraph
    from langgraph.graph import StateGraph
    graph = StateGraph(...)
    app = graph.compile(checkpointer=saver)
    result = await app.ainvoke(
        {"messages": [...]},
        config={"configurable": {"thread_id": "abc123"}},
    )

Requirements
------------
Install the ``langgraph`` extra to use this class::

    pip install "mnemora[langgraph]"

The module can be *imported* without langgraph installed, but
``MnemoraCheckpointSaver(...)`` will raise ``ImportError`` at
instantiation time.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

try:
    from langchain_core.runnables import RunnableConfig
    from langgraph.checkpoint.base import (
        BaseCheckpointSaver,
        Checkpoint,
        CheckpointMetadata,
        CheckpointTuple,
    )

    _HAS_LANGGRAPH = True
except ImportError:
    _HAS_LANGGRAPH = False
    # Stub base class so the module is importable without langgraph.
    # Instantiation raises ImportError; type checkers still resolve attributes.
    BaseCheckpointSaver = object  # type: ignore[assignment,misc]
    Checkpoint = dict  # type: ignore[assignment,misc]
    CheckpointMetadata = dict  # type: ignore[assignment,misc]
    CheckpointTuple = tuple  # type: ignore[assignment,misc]
    RunnableConfig = dict  # type: ignore[assignment,misc]


class MnemoraCheckpointSaver(BaseCheckpointSaver):  # type: ignore[misc]
    """LangGraph checkpoint saver that persists graph state to Mnemora.

    Maps LangGraph's ``thread_id`` + ``checkpoint_ns`` pair to Mnemora's
    ``agent_id`` / ``session_id`` pair.  Optimistic locking is forwarded
    transparently: the Mnemora version integer is stored in the returned
    ``RunnableConfig`` so that concurrent checkpoint writers get a proper
    ``MnemoraConflictError`` instead of a silent data-loss scenario.

    Parameters
    ----------
    client:
        An async ``MnemoraClient`` instance.  The saver is async-first;
        the synchronous ``get`` / ``put`` / ``list`` shims block the calling
        thread via ``asyncio.run()`` and must NOT be called from a running
        event loop.
    namespace:
        Prefix prepended to every ``agent_id``, e.g. ``"langgraph"``
        produces ``"langgraph:thread-abc"`` as the Mnemora agent ID.
        Isolates checkpoint data from other SDK usage on the same account.
    """

    def __init__(self, client: Any, namespace: str = "langgraph") -> None:
        if not _HAS_LANGGRAPH:
            raise ImportError(
                "langgraph and langchain-core are required for MnemoraCheckpointSaver. "
                "Install them with: pip install 'mnemora[langgraph]'"
            )
        super().__init__()
        self.client = client
        self.namespace = namespace

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _agent_id(self, thread_id: str) -> str:
        """Build the Mnemora agent_id from a LangGraph thread_id.

        Args:
            thread_id: LangGraph thread identifier.

        Returns:
            Namespaced agent ID string, e.g. ``"langgraph:thread-abc"``.
        """
        return f"{self.namespace}:{thread_id}"

    def _checkpoint_ns(self, config: RunnableConfig) -> str:
        """Extract the checkpoint namespace from a LangGraph config.

        Args:
            config: LangGraph ``RunnableConfig`` dict.

        Returns:
            The ``checkpoint_ns`` string, or ``""`` when absent.
        """
        return config.get("configurable", {}).get("checkpoint_ns", "")

    def _session_id(self, config: RunnableConfig) -> str:
        """Build the Mnemora session_id from the LangGraph checkpoint namespace.

        Args:
            config: LangGraph ``RunnableConfig`` dict.

        Returns:
            ``"ns:<checkpoint_ns>"`` or ``"default"`` for the root namespace.
        """
        ns = self._checkpoint_ns(config)
        return f"ns:{ns}" if ns else "default"

    # ------------------------------------------------------------------
    # Async interface (primary)
    # ------------------------------------------------------------------

    async def aget(self, config: RunnableConfig) -> Checkpoint | None:
        """Load the latest checkpoint for a thread.

        Args:
            config: LangGraph config dict with ``configurable.thread_id``.

        Returns:
            The deserialised ``Checkpoint`` dict, or ``None`` if no checkpoint
            has been saved for this thread yet.

        Raises:
            MnemoraAuthError: If the API key is invalid.
            MnemoraError: On unexpected API failures.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        try:
            state = await self.client.get_state(
                agent_id=self._agent_id(thread_id),
                session_id=self._session_id(config),
            )
        except MnemoraNotFoundError:
            return None

        return state.data.get("checkpoint")

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Load the latest checkpoint as a CheckpointTuple.

        This satisfies the BaseCheckpointSaver interface when LangGraph calls
        ``aget_tuple`` instead of ``aget``.

        Args:
            config: LangGraph config dict with ``configurable.thread_id``.

        Returns:
            A ``CheckpointTuple`` or ``None`` when no checkpoint exists.

        Raises:
            MnemoraAuthError: If the API key is invalid.
            MnemoraError: On unexpected API failures.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return None

        try:
            state = await self.client.get_state(
                agent_id=self._agent_id(thread_id),
                session_id=self._session_id(config),
            )
        except MnemoraNotFoundError:
            return None

        checkpoint_data = state.data.get("checkpoint")
        if checkpoint_data is None:
            return None

        metadata = state.data.get("metadata", {})
        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": self._checkpoint_ns(config),
                    "checkpoint_version": state.version,
                }
            },
            checkpoint=checkpoint_data,
            metadata=metadata,
            parent_config=None,
        )

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any] | None = None,
    ) -> RunnableConfig:
        """Save a checkpoint for a thread.

        Creates a new state record on first call; uses optimistic locking
        on subsequent calls to prevent concurrent-write data loss.

        Args:
            config: LangGraph config with ``configurable.thread_id``.
            checkpoint: The checkpoint payload to persist.
            metadata: LangGraph checkpoint metadata (step count, writes, etc.).
            new_versions: Optional channel version map from LangGraph.

        Returns:
            Updated ``RunnableConfig`` containing ``checkpoint_version`` for
            use in the next ``aput`` call.

        Raises:
            ValueError: If ``configurable.thread_id`` is absent from *config*.
            MnemoraConflictError: On optimistic-locking version mismatch.
            MnemoraAuthError: If the API key is invalid.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            raise ValueError("config must contain configurable.thread_id")

        agent_id = self._agent_id(thread_id)
        session_id = self._session_id(config)

        data: dict[str, Any] = {
            "checkpoint": checkpoint,
            "metadata": metadata if isinstance(metadata, dict) else {},
        }
        if new_versions is not None:
            data["channel_versions"] = new_versions

        current_version: int | None = config.get("configurable", {}).get(
            "checkpoint_version"
        )

        if current_version is not None:
            # We already know the current version — update directly.
            result = await self.client.update_state(
                agent_id=agent_id,
                data=data,
                version=current_version,
                session_id=session_id,
            )
        else:
            # Unknown version: probe for an existing record first.
            try:
                existing = await self.client.get_state(
                    agent_id=agent_id, session_id=session_id
                )
                result = await self.client.update_state(
                    agent_id=agent_id,
                    data=data,
                    version=existing.version,
                    session_id=session_id,
                )
            except MnemoraNotFoundError:
                result = await self.client.store_state(
                    agent_id=agent_id,
                    data=data,
                    session_id=session_id,
                )

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": self._checkpoint_ns(config),
                "checkpoint_version": result.version,
            }
        }

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Persist pending channel writes for an in-progress checkpoint.

        LangGraph calls this method during graph execution to record
        intermediate writes before the final ``aput``.  Mnemora stores
        them as part of the checkpoint data under the ``pending_writes`` key.

        Args:
            config: LangGraph config with ``configurable.thread_id``.
            writes: List of ``(channel, value)`` tuples to persist.
            task_id: Unique identifier of the writing task.

        Raises:
            MnemoraAuthError: If the API key is invalid.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return

        agent_id = self._agent_id(thread_id)
        session_id = self._session_id(config)

        try:
            state = await self.client.get_state(
                agent_id=agent_id, session_id=session_id
            )
            existing_data: dict[str, Any] = dict(state.data)
            pending = existing_data.get("pending_writes", {})
            pending[task_id] = [list(w) for w in writes]
            existing_data["pending_writes"] = pending
            await self.client.update_state(
                agent_id=agent_id,
                data=existing_data,
                version=state.version,
                session_id=session_id,
            )
        except MnemoraNotFoundError:
            # No checkpoint yet — writes will be included when aput is called.
            pass

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int = 10,
    ) -> AsyncIterator[CheckpointTuple]:
        """List checkpoint history for a thread.

        The Mnemora state API stores only the *latest* version of each
        (agent_id, session_id) pair, so this method yields at most one
        ``CheckpointTuple``.

        Args:
            config: LangGraph config with ``configurable.thread_id``.
            filter: Metadata filter — not yet supported; ignored.
            before: Upper-bound config — not yet supported; ignored.
            limit: Maximum number of results (honoured; always ≤ 1 today).

        Yields:
            The current ``CheckpointTuple`` for the thread, if one exists.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        if config is None or limit <= 0:
            return

        thread_id = config.get("configurable", {}).get("thread_id")
        if not thread_id:
            return

        try:
            state = await self.client.get_state(
                agent_id=self._agent_id(thread_id),
                session_id=self._session_id(config),
            )
        except MnemoraNotFoundError:
            return

        checkpoint_data = state.data.get("checkpoint")
        if checkpoint_data is None:
            return

        metadata = state.data.get("metadata", {})
        yield CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": self._checkpoint_ns(config),
                    "checkpoint_version": state.version,
                }
            },
            checkpoint=checkpoint_data,
            metadata=metadata,
            parent_config=None,
        )

    # ------------------------------------------------------------------
    # Synchronous shims (required by BaseCheckpointSaver contract)
    # ------------------------------------------------------------------

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        """Synchronous version of ``aget_tuple``.

        Args:
            config: LangGraph config with ``configurable.thread_id``.

        Returns:
            A ``CheckpointTuple`` or ``None``.

        Raises:
            RuntimeError: If called from inside a running event loop.
                Use ``aget_tuple()`` in async contexts.
        """
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot call sync get_tuple() from an async context. "
                "Use aget_tuple() instead."
            )
        except RuntimeError as exc:
            if "async context" in str(exc):
                raise
        return asyncio.run(self.aget_tuple(config))

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: dict[str, Any] | None = None,
    ) -> RunnableConfig:
        """Synchronous version of ``aput``.

        Args:
            config: LangGraph config with ``configurable.thread_id``.
            checkpoint: Checkpoint payload to persist.
            metadata: LangGraph checkpoint metadata.
            new_versions: Optional channel version map.

        Returns:
            Updated ``RunnableConfig``.

        Raises:
            RuntimeError: If called from inside a running event loop.
        """
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot call sync put() from an async context. Use aput() instead."
            )
        except RuntimeError as exc:
            if "async context" in str(exc):
                raise
        return asyncio.run(self.aput(config, checkpoint, metadata, new_versions))

    def put_writes(
        self,
        config: RunnableConfig,
        writes: list[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Synchronous version of ``aput_writes``.

        Args:
            config: LangGraph config with ``configurable.thread_id``.
            writes: List of ``(channel, value)`` tuples.
            task_id: Writing-task identifier.

        Raises:
            RuntimeError: If called from inside a running event loop.
        """
        import asyncio

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot call sync put_writes() from an async context. "
                "Use aput_writes() instead."
            )
        except RuntimeError as exc:
            if "async context" in str(exc):
                raise
        asyncio.run(self.aput_writes(config, writes, task_id))

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int = 10,
    ) -> list[CheckpointTuple]:
        """Synchronous version of ``alist`` — returns a list instead of an async iterator.

        Args:
            config: LangGraph config with ``configurable.thread_id``.
            filter: Metadata filter (not yet supported).
            before: Upper-bound config (not yet supported).
            limit: Maximum number of results.

        Returns:
            List of ``CheckpointTuple`` objects (at most one today).

        Raises:
            RuntimeError: If called from inside a running event loop.
        """
        import asyncio

        async def _collect() -> list[CheckpointTuple]:
            results: list[CheckpointTuple] = []
            async for item in self.alist(
                config, filter=filter, before=before, limit=limit
            ):
                results.append(item)
            return results

        try:
            asyncio.get_running_loop()
            raise RuntimeError(
                "Cannot call sync list() from an async context. Use alist() instead."
            )
        except RuntimeError as exc:
            if "async context" in str(exc):
                raise
        return asyncio.run(_collect())
