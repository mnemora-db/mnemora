"""Tests for Mnemora framework integrations.

These tests do NOT require langgraph, langchain, or crewai to be installed.
All framework base classes are replaced with lightweight stubs so the
integration logic can be exercised with plain ``unittest.mock`` objects.

Test layout
-----------
1.  LangGraph — MnemoraCheckpointSaver (async interface)
2.  LangGraph — MnemoraCheckpointSaver (sync shims raise in async context)
3.  LangChain — MnemoraMemory (sync client path)
4.  CrewAI    — MnemoraCrewStorage (sync client path)
"""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from mnemora.exceptions import MnemoraNotFoundError
from mnemora.models import EpisodeResponse, PurgeResponse, StateResponse

# ---------------------------------------------------------------------------
# Framework stub injection
#
# We inject minimal stub modules into sys.modules BEFORE importing the
# integration modules so that the "try: import langgraph ..." blocks inside
# them resolve to our stubs instead of raising ImportError.
# ---------------------------------------------------------------------------


def _make_stub_modules() -> None:
    """Inject stub framework modules so integrations can be imported."""

    # ---- langchain_core stubs ----
    lc_core = types.ModuleType("langchain_core")
    lc_core_runnables = types.ModuleType("langchain_core.runnables")
    lc_core_messages = types.ModuleType("langchain_core.messages")
    lc_core_chat_history = types.ModuleType("langchain_core.chat_history")

    # RunnableConfig is just a dict alias in practice
    lc_core_runnables.RunnableConfig = dict  # type: ignore[attr-defined]

    # Minimal BaseMessage hierarchy
    class BaseMessage:
        def __init__(self, content: str, **kwargs: Any) -> None:
            self.content = content
            self.type: str = "base"

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}(content={self.content!r})"

    class HumanMessage(BaseMessage):
        def __init__(self, content: str, **kwargs: Any) -> None:
            super().__init__(content, **kwargs)
            self.type = "human"

    class AIMessage(BaseMessage):
        def __init__(self, content: str, **kwargs: Any) -> None:
            super().__init__(content, **kwargs)
            self.type = "ai"

    class SystemMessage(BaseMessage):
        def __init__(self, content: str, **kwargs: Any) -> None:
            super().__init__(content, **kwargs)
            self.type = "system"

    def message_to_dict(msg: BaseMessage) -> dict[str, Any]:
        return {"type": msg.type, "data": {"content": msg.content}}

    def messages_from_dict(dicts: list[dict[str, Any]]) -> list[BaseMessage]:
        result = []
        for d in dicts:
            msg_type = d.get("type", "human")
            content = d.get("data", {}).get("content", "")
            if msg_type == "ai":
                result.append(AIMessage(content=content))
            elif msg_type == "system":
                result.append(SystemMessage(content=content))
            else:
                result.append(HumanMessage(content=content))
        return result

    class BaseChatMessageHistory:
        pass

    lc_core_messages.BaseMessage = BaseMessage  # type: ignore[attr-defined]
    lc_core_messages.HumanMessage = HumanMessage  # type: ignore[attr-defined]
    lc_core_messages.AIMessage = AIMessage  # type: ignore[attr-defined]
    lc_core_messages.SystemMessage = SystemMessage  # type: ignore[attr-defined]
    lc_core_messages.message_to_dict = message_to_dict  # type: ignore[attr-defined]
    lc_core_messages.messages_from_dict = messages_from_dict  # type: ignore[attr-defined]
    lc_core_chat_history.BaseChatMessageHistory = BaseChatMessageHistory  # type: ignore[attr-defined]

    sys.modules.setdefault("langchain_core", lc_core)
    sys.modules.setdefault("langchain_core.runnables", lc_core_runnables)
    sys.modules.setdefault("langchain_core.messages", lc_core_messages)
    sys.modules.setdefault("langchain_core.chat_history", lc_core_chat_history)

    # ---- langgraph stubs ----
    lg = types.ModuleType("langgraph")
    lg_checkpoint = types.ModuleType("langgraph.checkpoint")
    lg_checkpoint_base = types.ModuleType("langgraph.checkpoint.base")

    class CheckpointTuple:
        def __init__(
            self,
            *,
            config: dict[str, Any],
            checkpoint: dict[str, Any],
            metadata: dict[str, Any],
            parent_config: Any = None,
        ) -> None:
            self.config = config
            self.checkpoint = checkpoint
            self.metadata = metadata
            self.parent_config = parent_config

        def __repr__(self) -> str:
            return (
                f"CheckpointTuple(config={self.config!r}, "
                f"checkpoint={self.checkpoint!r})"
            )

    class BaseCheckpointSaver:
        pass

    lg_checkpoint_base.BaseCheckpointSaver = BaseCheckpointSaver  # type: ignore[attr-defined]
    lg_checkpoint_base.Checkpoint = dict  # type: ignore[attr-defined]
    lg_checkpoint_base.CheckpointMetadata = dict  # type: ignore[attr-defined]
    lg_checkpoint_base.CheckpointTuple = CheckpointTuple  # type: ignore[attr-defined]

    sys.modules.setdefault("langgraph", lg)
    sys.modules.setdefault("langgraph.checkpoint", lg_checkpoint)
    sys.modules.setdefault("langgraph.checkpoint.base", lg_checkpoint_base)

    # ---- crewai stubs ----
    crewai_mod = types.ModuleType("crewai")
    crewai_memory = types.ModuleType("crewai.memory")
    crewai_memory_storage = types.ModuleType("crewai.memory.storage")
    crewai_memory_storage_base = types.ModuleType("crewai.memory.storage.base")

    class Storage:
        pass

    crewai_memory_storage_base.Storage = Storage  # type: ignore[attr-defined]
    crewai_memory_storage.Storage = Storage  # type: ignore[attr-defined]

    sys.modules.setdefault("crewai", crewai_mod)
    sys.modules.setdefault("crewai.memory", crewai_memory)
    sys.modules.setdefault("crewai.memory.storage", crewai_memory_storage)
    sys.modules.setdefault("crewai.memory.storage.base", crewai_memory_storage_base)


# Inject stubs before importing the integration modules.
_make_stub_modules()

# Now import the integrations — they will resolve framework imports from stubs.
from mnemora.integrations.crewai import MnemoraCrewStorage  # noqa: E402
from mnemora.integrations.langchain import MnemoraMemory  # noqa: E402
from mnemora.integrations.langgraph import MnemoraCheckpointSaver  # noqa: E402

# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------

_STATE_V1: dict[str, Any] = {
    "agent_id": "langgraph:thread-abc",
    "session_id": "default",
    "data": {
        "checkpoint": {"ts": "2026-03-01T00:00:00Z", "channel_values": {}},
        "metadata": {"step": 0},
    },
    "version": 1,
    "created_at": "2026-03-01T00:00:00Z",
    "updated_at": "2026-03-01T00:00:00Z",
    "expires_at": None,
}

_STATE_V2: dict[str, Any] = {**_STATE_V1, "version": 2}

_EPISODE_DATA: dict[str, Any] = {
    "id": "ep-1",
    "agent_id": "my-agent",
    "session_id": "sess-1",
    "type": "conversation",
    "content": {"type": "human", "data": {"content": "Hello!"}},
    "metadata": {"langchain": True},
    "timestamp": "2026-03-01T10:00:00Z",
}

_PURGE_DATA: dict[str, Any] = {
    "agent_id": "my-agent",
    "deleted": {"state": 0, "semantic": 0, "episodic": 5, "s3_objects": 0},
}


def _state(**kwargs: Any) -> StateResponse:
    """Build a StateResponse with optional field overrides."""
    return StateResponse(**{**_STATE_V1, **kwargs})


def _episode(**kwargs: Any) -> EpisodeResponse:
    """Build an EpisodeResponse with optional field overrides."""
    return EpisodeResponse(**{**_EPISODE_DATA, **kwargs})


def _purge(**kwargs: Any) -> PurgeResponse:
    return PurgeResponse(**{**_PURGE_DATA, **kwargs})


def _lg_config(
    thread_id: str = "thread-abc",
    checkpoint_ns: str = "",
    checkpoint_version: int | None = None,
) -> dict[str, Any]:
    """Build a minimal LangGraph RunnableConfig dict."""
    configurable: dict[str, Any] = {"thread_id": thread_id}
    if checkpoint_ns:
        configurable["checkpoint_ns"] = checkpoint_ns
    if checkpoint_version is not None:
        configurable["checkpoint_version"] = checkpoint_version
    return {"configurable": configurable}


# ---------------------------------------------------------------------------
# 1. MnemoraCheckpointSaver — async interface
# ---------------------------------------------------------------------------


class TestMnemoraCheckpointSaverAgentId:
    """Unit tests for internal helper methods."""

    def setup_method(self) -> None:
        self.saver = MnemoraCheckpointSaver(client=MagicMock(), namespace="langgraph")

    def test_agent_id_default_namespace(self) -> None:
        assert self.saver._agent_id("thread-abc") == "langgraph:thread-abc"

    def test_agent_id_custom_namespace(self) -> None:
        saver = MnemoraCheckpointSaver(client=MagicMock(), namespace="myapp")
        assert saver._agent_id("t1") == "myapp:t1"

    def test_session_id_empty_ns(self) -> None:
        config = _lg_config()
        assert self.saver._session_id(config) == "default"

    def test_session_id_with_ns(self) -> None:
        config = _lg_config(checkpoint_ns="subgraph")
        assert self.saver._session_id(config) == "ns:subgraph"

    def test_checkpoint_ns_absent(self) -> None:
        assert self.saver._checkpoint_ns({"configurable": {}}) == ""

    def test_checkpoint_ns_present(self) -> None:
        config = _lg_config(checkpoint_ns="x")
        assert self.saver._checkpoint_ns(config) == "x"


class TestMnemoraCheckpointSaverAget:
    """Tests for aget() and aget_tuple()."""

    @pytest.mark.asyncio
    async def test_aget_returns_checkpoint_when_state_exists(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(return_value=_state())
        saver = MnemoraCheckpointSaver(client=client)

        result = await saver.aget(_lg_config())

        assert result == _STATE_V1["data"]["checkpoint"]
        client.get_state.assert_awaited_once_with(
            agent_id="langgraph:thread-abc", session_id="default"
        )

    @pytest.mark.asyncio
    async def test_aget_returns_none_when_not_found(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(side_effect=MnemoraNotFoundError())
        saver = MnemoraCheckpointSaver(client=client)

        result = await saver.aget(_lg_config())

        assert result is None

    @pytest.mark.asyncio
    async def test_aget_returns_none_when_no_thread_id(self) -> None:
        client = MagicMock()
        saver = MnemoraCheckpointSaver(client=client)

        result = await saver.aget({"configurable": {}})

        assert result is None
        client.get_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_aget_returns_none_when_checkpoint_key_absent(self) -> None:
        state = _state(data={"metadata": {}})  # no "checkpoint" key
        client = MagicMock()
        client.get_state = AsyncMock(return_value=state)
        saver = MnemoraCheckpointSaver(client=client)

        result = await saver.aget(_lg_config())

        assert result is None

    @pytest.mark.asyncio
    async def test_aget_tuple_returns_tuple_when_state_exists(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(return_value=_state())
        saver = MnemoraCheckpointSaver(client=client)

        result = await saver.aget_tuple(_lg_config())

        assert result is not None
        assert result.checkpoint == _STATE_V1["data"]["checkpoint"]
        assert result.metadata == _STATE_V1["data"]["metadata"]
        assert result.config["configurable"]["thread_id"] == "thread-abc"
        assert result.config["configurable"]["checkpoint_version"] == 1

    @pytest.mark.asyncio
    async def test_aget_tuple_returns_none_when_not_found(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(side_effect=MnemoraNotFoundError())
        saver = MnemoraCheckpointSaver(client=client)

        result = await saver.aget_tuple(_lg_config())

        assert result is None

    @pytest.mark.asyncio
    async def test_aget_tuple_uses_checkpoint_ns_in_session_id(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(return_value=_state(session_id="ns:sub"))
        saver = MnemoraCheckpointSaver(client=client)

        await saver.aget_tuple(_lg_config(checkpoint_ns="sub"))

        client.get_state.assert_awaited_once_with(
            agent_id="langgraph:thread-abc", session_id="ns:sub"
        )


class TestMnemoraCheckpointSaverAput:
    """Tests for aput()."""

    @pytest.mark.asyncio
    async def test_aput_creates_new_state_when_not_found(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(side_effect=MnemoraNotFoundError())
        client.store_state = AsyncMock(return_value=_state(version=1))
        saver = MnemoraCheckpointSaver(client=client)

        checkpoint = {"ts": "2026-03-01T00:00:00Z", "channel_values": {}}
        metadata = {"step": 0}
        config = _lg_config()

        result = await saver.aput(config, checkpoint, metadata)

        client.store_state.assert_awaited_once()
        call_kwargs = client.store_state.call_args.kwargs
        assert call_kwargs["agent_id"] == "langgraph:thread-abc"
        assert call_kwargs["data"]["checkpoint"] == checkpoint
        assert call_kwargs["data"]["metadata"] == metadata

        assert result["configurable"]["thread_id"] == "thread-abc"
        assert result["configurable"]["checkpoint_version"] == 1

    @pytest.mark.asyncio
    async def test_aput_updates_existing_state_when_found(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(return_value=_state(version=3))
        client.update_state = AsyncMock(return_value=_state(version=4))
        saver = MnemoraCheckpointSaver(client=client)

        checkpoint = {"ts": "t2"}
        metadata = {"step": 1}
        config = _lg_config()

        result = await saver.aput(config, checkpoint, metadata)

        client.update_state.assert_awaited_once()
        call_kwargs = client.update_state.call_args.kwargs
        assert call_kwargs["version"] == 3
        assert call_kwargs["agent_id"] == "langgraph:thread-abc"
        assert result["configurable"]["checkpoint_version"] == 4

    @pytest.mark.asyncio
    async def test_aput_uses_version_from_config(self) -> None:
        """When config already carries checkpoint_version, skip get_state probe."""
        client = MagicMock()
        client.update_state = AsyncMock(return_value=_state(version=6))
        saver = MnemoraCheckpointSaver(client=client)

        config = _lg_config(checkpoint_version=5)
        result = await saver.aput(config, {}, {})

        client.get_state.assert_not_called()
        call_kwargs = client.update_state.call_args.kwargs
        assert call_kwargs["version"] == 5
        assert result["configurable"]["checkpoint_version"] == 6

    @pytest.mark.asyncio
    async def test_aput_includes_new_versions_in_data(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(side_effect=MnemoraNotFoundError())
        client.store_state = AsyncMock(return_value=_state())
        saver = MnemoraCheckpointSaver(client=client)

        new_versions = {"inbox": "v2"}
        await saver.aput(_lg_config(), {}, {}, new_versions=new_versions)

        stored_data = client.store_state.call_args.kwargs["data"]
        assert stored_data["channel_versions"] == new_versions

    @pytest.mark.asyncio
    async def test_aput_raises_value_error_without_thread_id(self) -> None:
        saver = MnemoraCheckpointSaver(client=MagicMock())

        with pytest.raises(ValueError, match="thread_id"):
            await saver.aput({"configurable": {}}, {}, {})

    @pytest.mark.asyncio
    async def test_aput_returns_checkpoint_ns_in_config(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(side_effect=MnemoraNotFoundError())
        client.store_state = AsyncMock(return_value=_state())
        saver = MnemoraCheckpointSaver(client=client)

        config = _lg_config(checkpoint_ns="subgraph")
        result = await saver.aput(config, {}, {})

        assert result["configurable"]["checkpoint_ns"] == "subgraph"


class TestMnemoraCheckpointSaverAlist:
    """Tests for alist()."""

    @pytest.mark.asyncio
    async def test_alist_yields_tuple_when_state_exists(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(return_value=_state())
        saver = MnemoraCheckpointSaver(client=client)

        results = []
        async for item in saver.alist(_lg_config()):
            results.append(item)

        assert len(results) == 1
        assert results[0].checkpoint == _STATE_V1["data"]["checkpoint"]
        assert results[0].config["configurable"]["checkpoint_version"] == 1

    @pytest.mark.asyncio
    async def test_alist_yields_nothing_when_not_found(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(side_effect=MnemoraNotFoundError())
        saver = MnemoraCheckpointSaver(client=client)

        results = []
        async for item in saver.alist(_lg_config()):
            results.append(item)

        assert results == []

    @pytest.mark.asyncio
    async def test_alist_yields_nothing_when_config_is_none(self) -> None:
        saver = MnemoraCheckpointSaver(client=MagicMock())

        results = []
        async for item in saver.alist(None):
            results.append(item)

        assert results == []

    @pytest.mark.asyncio
    async def test_alist_yields_nothing_when_no_thread_id(self) -> None:
        saver = MnemoraCheckpointSaver(client=MagicMock())

        results = []
        async for item in saver.alist({"configurable": {}}):
            results.append(item)

        assert results == []

    @pytest.mark.asyncio
    async def test_alist_yields_nothing_when_no_checkpoint_in_data(self) -> None:
        state = _state(data={"metadata": {}})
        client = MagicMock()
        client.get_state = AsyncMock(return_value=state)
        saver = MnemoraCheckpointSaver(client=client)

        results = []
        async for item in saver.alist(_lg_config()):
            results.append(item)

        assert results == []

    @pytest.mark.asyncio
    async def test_alist_respects_limit_zero(self) -> None:
        """limit=0 should yield nothing."""
        client = MagicMock()
        client.get_state = AsyncMock(return_value=_state())
        saver = MnemoraCheckpointSaver(client=client)

        results = []
        async for item in saver.alist(_lg_config(), limit=0):
            results.append(item)

        assert results == []
        client.get_state.assert_not_called()


class TestMnemoraCheckpointSaverAputWrites:
    """Tests for aput_writes()."""

    @pytest.mark.asyncio
    async def test_aput_writes_updates_pending_writes(self) -> None:
        client = MagicMock()
        client.get_state = AsyncMock(
            return_value=_state(data={"checkpoint": {}, "metadata": {}})
        )
        client.update_state = AsyncMock(return_value=_state())
        saver = MnemoraCheckpointSaver(client=client)

        writes = [("inbox", "msg1"), ("outbox", "msg2")]
        await saver.aput_writes(_lg_config(), writes, task_id="task-1")

        client.update_state.assert_awaited_once()
        updated_data = client.update_state.call_args.kwargs["data"]
        assert "task-1" in updated_data["pending_writes"]
        assert updated_data["pending_writes"]["task-1"] == [
            ["inbox", "msg1"],
            ["outbox", "msg2"],
        ]

    @pytest.mark.asyncio
    async def test_aput_writes_no_op_when_not_found(self) -> None:
        """When no checkpoint exists yet, aput_writes is a safe no-op."""
        client = MagicMock()
        client.get_state = AsyncMock(side_effect=MnemoraNotFoundError())
        saver = MnemoraCheckpointSaver(client=client)

        # Must not raise
        await saver.aput_writes(_lg_config(), [("ch", "v")], task_id="t1")
        client.update_state.assert_not_called()

    @pytest.mark.asyncio
    async def test_aput_writes_no_op_when_no_thread_id(self) -> None:
        client = MagicMock()
        saver = MnemoraCheckpointSaver(client=client)

        await saver.aput_writes({"configurable": {}}, [], task_id="t1")

        client.get_state.assert_not_called()


class TestMnemoraCheckpointSaverSyncShims:
    """Sync shims must raise RuntimeError when called from an async context."""

    def test_put_raises_in_async_context(self) -> None:
        """put() detects a running loop and raises RuntimeError."""
        import asyncio

        saver = MnemoraCheckpointSaver(client=MagicMock())

        async def _inner() -> None:
            with pytest.raises(RuntimeError, match="async context"):
                saver.put(_lg_config(), {}, {})

        asyncio.run(_inner())

    def test_list_raises_in_async_context(self) -> None:
        import asyncio

        saver = MnemoraCheckpointSaver(client=MagicMock())

        async def _inner() -> None:
            with pytest.raises(RuntimeError, match="async context"):
                saver.list(_lg_config())

        asyncio.run(_inner())

    def test_get_tuple_raises_in_async_context(self) -> None:
        import asyncio

        saver = MnemoraCheckpointSaver(client=MagicMock())

        async def _inner() -> None:
            with pytest.raises(RuntimeError, match="async context"):
                saver.get_tuple(_lg_config())

        asyncio.run(_inner())

    def test_put_writes_raises_in_async_context(self) -> None:
        import asyncio

        saver = MnemoraCheckpointSaver(client=MagicMock())

        async def _inner() -> None:
            with pytest.raises(RuntimeError, match="async context"):
                saver.put_writes(_lg_config(), [], "t1")

        asyncio.run(_inner())


# ---------------------------------------------------------------------------
# 2. MnemoraMemory (LangChain integration) — sync client path
# ---------------------------------------------------------------------------


class TestMnemoraMemory:
    """Tests for MnemoraMemory using a sync MnemoraSync mock client."""

    def _make_memory(self, client: Any = None) -> MnemoraMemory:
        if client is None:
            client = MagicMock()
        return MnemoraMemory(
            client=client, agent_id="my-agent", session_id="sess-1", sync=True
        )

    def test_add_message_calls_store_episode(self) -> None:
        client = MagicMock()
        memory = self._make_memory(client)

        # Import from stub
        HumanMessage = sys.modules["langchain_core.messages"].HumanMessage
        memory.add_message(HumanMessage(content="Hello!"))

        client.store_episode.assert_called_once()
        call_kwargs = client.store_episode.call_args.kwargs
        assert call_kwargs["agent_id"] == "my-agent"
        assert call_kwargs["session_id"] == "sess-1"
        assert call_kwargs["type"] == "conversation"
        assert call_kwargs["metadata"] == {"langchain": True}
        # Content should be a message dict with "type" key
        assert "type" in call_kwargs["content"]
        assert call_kwargs["content"]["type"] == "human"

    def test_add_user_message_stores_human_message(self) -> None:
        client = MagicMock()
        memory = self._make_memory(client)

        memory.add_user_message("Hi there")

        call_kwargs = client.store_episode.call_args.kwargs
        assert call_kwargs["content"]["type"] == "human"

    def test_add_ai_message_stores_ai_message(self) -> None:
        client = MagicMock()
        memory = self._make_memory(client)

        memory.add_ai_message("I can help with that.")

        call_kwargs = client.store_episode.call_args.kwargs
        assert call_kwargs["content"]["type"] == "ai"

    def test_messages_retrieves_and_deserialises_episodes(self) -> None:
        ep = _episode(content={"type": "human", "data": {"content": "Hello!"}})
        client = MagicMock()
        client.get_session_episodes.return_value = [ep]
        memory = self._make_memory(client)

        msgs = memory.messages

        client.get_session_episodes.assert_called_once_with(
            agent_id="my-agent", session_id="sess-1"
        )
        assert len(msgs) == 1
        assert msgs[0].content == "Hello!"

    def test_messages_handles_ai_message_type(self) -> None:
        ep = _episode(content={"type": "ai", "data": {"content": "Sure!"}})
        client = MagicMock()
        client.get_session_episodes.return_value = [ep]
        memory = self._make_memory(client)

        msgs = memory.messages

        AIMessage = sys.modules["langchain_core.messages"].AIMessage
        assert isinstance(msgs[0], AIMessage)
        assert msgs[0].content == "Sure!"

    def test_messages_handles_dict_with_role_fallback(self) -> None:
        """Episode content without a 'type' key uses role-based heuristic."""
        ep = _episode(content={"role": "assistant", "content": "Got it."})
        client = MagicMock()
        client.get_session_episodes.return_value = [ep]
        memory = self._make_memory(client)

        msgs = memory.messages

        AIMessage = sys.modules["langchain_core.messages"].AIMessage
        assert isinstance(msgs[0], AIMessage)

    def test_messages_handles_plain_string_content(self) -> None:
        ep = _episode(content="raw text")
        client = MagicMock()
        client.get_session_episodes.return_value = [ep]
        memory = self._make_memory(client)

        msgs = memory.messages

        HumanMessage = sys.modules["langchain_core.messages"].HumanMessage
        assert isinstance(msgs[0], HumanMessage)
        assert msgs[0].content == "raw text"

    def test_messages_returns_empty_list_when_no_episodes(self) -> None:
        client = MagicMock()
        client.get_session_episodes.return_value = []
        memory = self._make_memory(client)

        assert memory.messages == []

    def test_clear_calls_purge_agent(self) -> None:
        client = MagicMock()
        memory = self._make_memory(client)

        memory.clear()

        client.purge_agent.assert_called_once_with("my-agent")

    def test_default_session_id_is_default(self) -> None:
        client = MagicMock()
        memory = MnemoraMemory(client=client, agent_id="ag1", sync=True)
        assert memory.session_id == "default"


# ---------------------------------------------------------------------------
# 3. MnemoraCrewStorage (CrewAI integration) — sync client path
# ---------------------------------------------------------------------------


class TestMnemoraCrewStorage:
    """Tests for MnemoraCrewStorage using a sync MnemoraSync mock client."""

    def _make_storage(self, client: Any = None) -> MnemoraCrewStorage:
        if client is None:
            client = MagicMock()
        return MnemoraCrewStorage(client=client, agent_id="crew-agent")

    # ---- save ----

    def test_save_new_key_calls_store_state(self) -> None:
        client = MagicMock()
        client.get_state.side_effect = MnemoraNotFoundError()
        client.store_state.return_value = _state(
            agent_id="crew-agent", session_id="plan"
        )
        storage = self._make_storage(client)

        storage.save("plan", {"steps": ["a", "b"]})

        client.store_state.assert_called_once()
        call_kwargs = client.store_state.call_args.kwargs
        assert call_kwargs["agent_id"] == "crew-agent"
        assert call_kwargs["session_id"] == "plan"
        assert call_kwargs["data"] == {"steps": ["a", "b"]}

    def test_save_existing_key_calls_update_state(self) -> None:
        existing = _state(agent_id="crew-agent", session_id="plan", version=2)
        client = MagicMock()
        client.get_state.return_value = existing
        client.update_state.return_value = _state(
            agent_id="crew-agent", session_id="plan", version=3
        )
        storage = self._make_storage(client)

        storage.save("plan", {"steps": ["a", "b", "c"]})

        client.update_state.assert_called_once()
        call_kwargs = client.update_state.call_args.kwargs
        assert call_kwargs["version"] == 2
        assert call_kwargs["data"] == {"steps": ["a", "b", "c"]}

    def test_save_wraps_scalar_value_in_dict(self) -> None:
        client = MagicMock()
        client.get_state.side_effect = MnemoraNotFoundError()
        client.store_state.return_value = _state()
        storage = self._make_storage(client)

        storage.save("counter", 42)

        stored_data = client.store_state.call_args.kwargs["data"]
        assert stored_data == {"value": 42}

    def test_save_passes_dict_value_unchanged(self) -> None:
        client = MagicMock()
        client.get_state.side_effect = MnemoraNotFoundError()
        client.store_state.return_value = _state()
        storage = self._make_storage(client)

        storage.save("config", {"a": 1, "b": 2})

        stored_data = client.store_state.call_args.kwargs["data"]
        assert stored_data == {"a": 1, "b": 2}

    # ---- load ----

    def test_load_returns_data_when_key_exists(self) -> None:
        state = _state(
            agent_id="crew-agent",
            session_id="plan",
            data={"steps": ["a", "b"]},
        )
        client = MagicMock()
        client.get_state.return_value = state
        storage = self._make_storage(client)

        result = storage.load("plan")

        assert result == {"steps": ["a", "b"]}
        client.get_state.assert_called_once_with(
            agent_id="crew-agent", session_id="plan"
        )

    def test_load_returns_none_for_missing_key(self) -> None:
        client = MagicMock()
        client.get_state.side_effect = MnemoraNotFoundError()
        storage = self._make_storage(client)

        result = storage.load("missing")

        assert result is None

    # ---- delete ----

    def test_delete_calls_delete_state(self) -> None:
        client = MagicMock()
        storage = self._make_storage(client)

        storage.delete("plan")

        client.delete_state.assert_called_once_with(
            agent_id="crew-agent", session_id="plan"
        )

    def test_delete_is_idempotent_for_missing_key(self) -> None:
        """Deleting a non-existent key must not raise."""
        client = MagicMock()
        client.delete_state.side_effect = MnemoraNotFoundError()
        storage = self._make_storage(client)

        storage.delete("missing")  # Should not raise

    # ---- list_keys ----

    def test_list_keys_returns_sessions(self) -> None:
        client = MagicMock()
        client.list_sessions.return_value = ["plan", "notes", "config"]
        storage = self._make_storage(client)

        keys = storage.list_keys()

        assert keys == ["plan", "notes", "config"]
        client.list_sessions.assert_called_once_with("crew-agent")

    def test_list_keys_returns_empty_when_no_sessions(self) -> None:
        client = MagicMock()
        client.list_sessions.return_value = []
        storage = self._make_storage(client)

        assert storage.list_keys() == []

    # ---- reset ----

    def test_reset_deletes_all_keys(self) -> None:
        client = MagicMock()
        client.list_sessions.return_value = ["k1", "k2", "k3"]
        storage = self._make_storage(client)

        storage.reset()

        assert client.delete_state.call_count == 3
        deleted_sessions = {
            call.kwargs["session_id"] for call in client.delete_state.call_args_list
        }
        assert deleted_sessions == {"k1", "k2", "k3"}

    def test_reset_is_idempotent_when_key_concurrently_removed(self) -> None:
        client = MagicMock()
        client.list_sessions.return_value = ["k1"]
        client.delete_state.side_effect = MnemoraNotFoundError()
        storage = self._make_storage(client)

        storage.reset()  # Should not raise

    # ---- search ----

    def test_search_returns_all_values(self) -> None:
        client = MagicMock()
        client.list_sessions.return_value = ["k1", "k2"]
        states = {
            "k1": _state(data={"val": 1}),
            "k2": _state(data={"val": 2}),
        }
        client.get_state.side_effect = lambda agent_id, session_id: states[session_id]
        storage = self._make_storage(client)

        results = storage.search("anything")

        assert len(results) == 2
        values = [r["val"] for r in results]
        assert set(values) == {1, 2}

    def test_search_skips_none_loads(self) -> None:
        client = MagicMock()
        client.list_sessions.return_value = ["k1"]
        client.get_state.side_effect = MnemoraNotFoundError()
        storage = self._make_storage(client)

        results = storage.search("query")

        assert results == []

    # ---- default agent_id ----

    def test_default_agent_id_is_crewai(self) -> None:
        client = MagicMock()
        storage = MnemoraCrewStorage(client=client)
        assert storage.agent_id == "crewai"


# ---------------------------------------------------------------------------
# 4. Import guard — modules importable even when stubs are absent
# ---------------------------------------------------------------------------


class TestImportGuards:
    """Verify ImportError is raised at instantiation, not at import time."""

    def test_checkpoint_saver_raises_when_langgraph_missing(self) -> None:
        """Removing the stubs and forcing _HAS_LANGGRAPH=False triggers ImportError."""
        import mnemora.integrations.langgraph as lg_mod

        original = lg_mod._HAS_LANGGRAPH
        try:
            lg_mod._HAS_LANGGRAPH = False
            with pytest.raises(ImportError, match="langgraph"):
                MnemoraCheckpointSaver(client=MagicMock())
        finally:
            lg_mod._HAS_LANGGRAPH = original

    def test_memory_raises_when_langchain_missing(self) -> None:
        import mnemora.integrations.langchain as lc_mod

        original = lc_mod._HAS_LANGCHAIN
        try:
            lc_mod._HAS_LANGCHAIN = False
            with pytest.raises(ImportError, match="langchain"):
                MnemoraMemory(client=MagicMock(), agent_id="a")
        finally:
            lc_mod._HAS_LANGCHAIN = original

    def test_crew_storage_instantiates_without_crewai(self) -> None:
        """MnemoraCrewStorage never raises at instantiation — no framework needed."""
        storage = MnemoraCrewStorage(client=MagicMock())
        assert storage.agent_id == "crewai"
