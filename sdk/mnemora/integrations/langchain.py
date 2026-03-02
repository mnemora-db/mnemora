"""LangChain chat message history backed by Mnemora episodic memory.

Each message is stored as an episode of type ``"conversation"`` under the
configured ``agent_id`` / ``session_id`` pair.  The episode ``content`` field
holds the LangChain message dict produced by ``message_to_dict()``, which is
invertible via ``messages_from_dict()``.

Usage::

    from mnemora import MnemoraSync
    from mnemora.integrations.langchain import MnemoraMemory

    client = MnemoraSync(api_key="mnm_...")
    memory = MnemoraMemory(client=client, agent_id="my-agent", session_id="sess-1")

    memory.add_user_message("Hello!")
    memory.add_ai_message("Hi there!")
    for msg in memory.messages:
        print(msg.content)

    # Use with LangChain LCEL chains that accept a history provider:
    from langchain_core.runnables.history import RunnableWithMessageHistory
    chain_with_history = RunnableWithMessageHistory(
        chain,
        lambda session_id: MnemoraMemory(
            client=client,
            agent_id="agent-1",
            session_id=session_id,
        ),
    )

Requirements
------------
Install the ``langchain`` extra to use this class::

    pip install "mnemora[langchain]"

The module can be *imported* without ``langchain-core`` installed, but
``MnemoraMemory(...)`` will raise ``ImportError`` at instantiation time.
"""

from __future__ import annotations

from typing import Any

try:
    from langchain_core.chat_history import BaseChatMessageHistory
    from langchain_core.messages import (
        AIMessage,
        BaseMessage,
        HumanMessage,
        SystemMessage,
        message_to_dict,
        messages_from_dict,
    )

    _HAS_LANGCHAIN = True
except ImportError:
    _HAS_LANGCHAIN = False
    BaseChatMessageHistory = object  # type: ignore[assignment,misc]
    BaseMessage = object  # type: ignore[assignment,misc]


class MnemoraMemory(BaseChatMessageHistory):  # type: ignore[misc]
    """LangChain chat message history backed by Mnemora episodic memory.

    Stores each message as an episode of type ``"conversation"`` so that
    the full interaction history is queryable by time range, filterable by
    session, and composable with other episodic memory (actions, observations).

    The ``messages`` property fetches all episodes for the session via
    ``GET /v1/memory/episodic/{agent_id}/sessions/{session_id}`` and
    deserialises them back into LangChain ``BaseMessage`` objects using the
    standard ``messages_from_dict`` helper.

    Parameters
    ----------
    client:
        A ``MnemoraSync`` instance (recommended) or an async ``MnemoraClient``
        instance.  When passing an async client, set ``sync=False`` and ensure
        the caller is *not* inside a running event loop.
    agent_id:
        Mnemora agent identifier that owns the conversation.
    session_id:
        Conversation session identifier.  Defaults to ``"default"``.
    sync:
        ``True`` (default) when *client* is a ``MnemoraSync`` instance.
        ``False`` when *client* is an async ``MnemoraClient`` — the class
        will use ``asyncio.run()`` which blocks the calling thread.
    """

    def __init__(
        self,
        client: Any,
        agent_id: str,
        session_id: str = "default",
        sync: bool = True,
    ) -> None:
        if not _HAS_LANGCHAIN:
            raise ImportError(
                "langchain-core is required for MnemoraMemory. "
                "Install it with: pip install 'mnemora[langchain]'"
            )
        self.client = client
        self.agent_id = agent_id
        self.session_id = session_id
        self._sync = sync

    # ------------------------------------------------------------------
    # BaseChatMessageHistory interface
    # ------------------------------------------------------------------

    @property
    def messages(self) -> list[BaseMessage]:
        """Retrieve all messages for this session in chronological order.

        Returns:
            List of ``BaseMessage`` subclass instances (``HumanMessage``,
            ``AIMessage``, ``SystemMessage``, etc.).
        """
        if self._sync:
            episodes = self.client.get_session_episodes(
                agent_id=self.agent_id,
                session_id=self.session_id,
            )
        else:
            import asyncio

            episodes = asyncio.run(
                self.client.get_session_episodes(
                    agent_id=self.agent_id,
                    session_id=self.session_id,
                )
            )

        result: list[BaseMessage] = []
        for ep in episodes:
            content = ep.content
            if isinstance(content, dict) and "type" in content:
                # Standard LangChain message dict — reconstruct via helper.
                msgs = messages_from_dict([content])
                result.extend(msgs)
            elif isinstance(content, dict):
                # Fallback: extract role + text heuristically.
                role = content.get("role", "human")
                text = str(content.get("content", content.get("message", content)))
                if role in ("ai", "assistant"):
                    result.append(AIMessage(content=text))
                elif role == "system":
                    result.append(SystemMessage(content=text))
                else:
                    result.append(HumanMessage(content=text))
            elif isinstance(content, str):
                result.append(HumanMessage(content=content))
        return result

    def add_message(self, message: BaseMessage) -> None:
        """Store a single message as a Mnemora episode.

        Args:
            message: Any ``BaseMessage`` subclass (``HumanMessage``,
                ``AIMessage``, ``SystemMessage``, …).
        """
        msg_dict = message_to_dict(message)

        if self._sync:
            self.client.store_episode(
                agent_id=self.agent_id,
                session_id=self.session_id,
                type="conversation",
                content=msg_dict,
                metadata={"langchain": True},
            )
        else:
            import asyncio

            asyncio.run(
                self.client.store_episode(
                    agent_id=self.agent_id,
                    session_id=self.session_id,
                    type="conversation",
                    content=msg_dict,
                    metadata={"langchain": True},
                )
            )

    def add_user_message(self, message: str) -> None:
        """Convenience method: append a ``HumanMessage``.

        Args:
            message: Plain-text user message to store.
        """
        self.add_message(HumanMessage(content=message))

    def add_ai_message(self, message: str) -> None:
        """Convenience method: append an ``AIMessage``.

        Args:
            message: Plain-text AI response to store.
        """
        self.add_message(AIMessage(content=message))

    def clear(self) -> None:
        """Remove all messages by issuing a GDPR purge for the agent.

        Warning: This deletes ALL memory (state, semantic, episodic) for
        the configured ``agent_id``, not only the current session.  If you
        need session-level clearing, use the Mnemora API directly.
        """
        if self._sync:
            self.client.purge_agent(self.agent_id)
        else:
            import asyncio

            asyncio.run(self.client.purge_agent(self.agent_id))
