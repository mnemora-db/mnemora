# LangGraph Integration

Persist LangGraph graph state across invocations using Mnemora as the checkpoint backend.

## Prerequisites

- A Mnemora API key
- LangGraph 0.2+ installed

## Install

```bash
pip install "mnemora[langgraph]"
```

This installs `mnemora`, `langgraph`, and `langchain-core`.

## How it works

`MnemoraCheckpointSaver` implements LangGraph's `BaseCheckpointSaver` interface. It maps each LangGraph `thread_id` to a Mnemora `agent_id`, and the checkpoint namespace to a Mnemora `session_id`. Graph state is stored in working memory (DynamoDB) with optimistic locking.

| LangGraph concept | Mnemora concept |
|-------------------|-----------------|
| `thread_id` | `agent_id` (prefixed with `"langgraph:"`) |
| `checkpoint_ns` | `session_id` |
| Checkpoint payload | Working memory `data` field |
| Version counter | DynamoDB optimistic lock `version` |

## Basic usage

```python
import asyncio
from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver
from langgraph.graph import StateGraph, MessagesState, START, END

async def main():
    async with MnemoraClient(api_key="mnm_...") as client:
        saver = MnemoraCheckpointSaver(client=client)

        # Build a minimal graph
        graph = StateGraph(MessagesState)
        graph.add_node("echo", lambda state: {"messages": state["messages"]})
        graph.add_edge(START, "echo")
        graph.add_edge("echo", END)

        app = graph.compile(checkpointer=saver)

        config = {"configurable": {"thread_id": "user-123"}}

        # First invocation — LangGraph saves a checkpoint automatically
        result = await app.ainvoke(
            {"messages": [{"role": "user", "content": "Hello"}]},
            config=config,
        )
        print(result["messages"][-1]["content"])

        # Second invocation — state is resumed from Mnemora
        result = await app.ainvoke(
            {"messages": [{"role": "user", "content": "What did I just say?"}]},
            config=config,
        )
        print(result["messages"][-1]["content"])

asyncio.run(main())
```

## Full chatbot example

This example builds a multi-turn chatbot with LangGraph + an OpenAI LLM. Each `thread_id` represents a separate user conversation, all persisted in Mnemora.

```python
import asyncio
from typing import Annotated
from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o-mini")

async def chat_node(state: MessagesState) -> dict:
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}

async def build_app(client: MnemoraClient):
    saver = MnemoraCheckpointSaver(client=client)
    graph = StateGraph(MessagesState)
    graph.add_node("chat", chat_node)
    graph.add_edge(START, "chat")
    graph.add_edge("chat", END)
    return graph.compile(checkpointer=saver)

async def main():
    async with MnemoraClient(api_key="mnm_...") as client:
        app = await build_app(client)

        # Simulate two turns for user "alice"
        config = {"configurable": {"thread_id": "alice"}}

        result = await app.ainvoke(
            {"messages": [{"role": "user", "content": "My name is Alice."}]},
            config=config,
        )
        print("Turn 1:", result["messages"][-1].content)

        result = await app.ainvoke(
            {"messages": [{"role": "user", "content": "What is my name?"}]},
            config=config,
        )
        print("Turn 2:", result["messages"][-1].content)
        # Output: Turn 2: Your name is Alice.

asyncio.run(main())
```

## Listing checkpoints for a thread

`MnemoraCheckpointSaver` stores only the most recent checkpoint per `(thread_id, checkpoint_ns)` pair. `alist` yields at most one result.

```python
import asyncio
from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver

async def main():
    async with MnemoraClient(api_key="mnm_...") as client:
        saver = MnemoraCheckpointSaver(client=client)
        config = {"configurable": {"thread_id": "alice"}}

        async for checkpoint_tuple in saver.alist(config):
            print("version:", checkpoint_tuple.config["configurable"]["checkpoint_version"])
            print("metadata:", checkpoint_tuple.metadata)

asyncio.run(main())
```

## Custom namespace

Use the `namespace` parameter to isolate checkpoint data from other SDK usage on the same account.

```python
saver = MnemoraCheckpointSaver(client=client, namespace="prod-chatbot")
# Stores checkpoints under agent_id "prod-chatbot:thread-abc"
```

The default namespace is `"langgraph"`.

## Async vs sync

`MnemoraCheckpointSaver` is async-first. LangGraph itself calls the async methods (`aget_tuple`, `aput`, `aput_writes`, `alist`) during graph execution.

Synchronous shims (`get_tuple`, `put`, `put_writes`, `list`) are available but raise `RuntimeError` if called from inside a running event loop. In async contexts — including all LangGraph graph runs — only the `a`-prefixed methods are called automatically.

## Error handling

```python
from mnemora import MnemoraConflictError, MnemoraAuthError

try:
    result = await app.ainvoke({"messages": [...]}, config=config)
except MnemoraConflictError:
    # Two concurrent writers hit a version mismatch — re-read and retry
    pass
except MnemoraAuthError:
    # API key is invalid or revoked
    pass
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: langgraph and langchain-core are required` | Package not installed | Run `pip install "mnemora[langgraph]"` |
| `ValueError: config must contain configurable.thread_id` | Missing thread config | Pass `config={"configurable": {"thread_id": "..."}}` to `ainvoke` |
| `RuntimeError: Cannot call sync ... from an async context` | Sync shim called in event loop | Use the `a`-prefixed async method instead |
| `MnemoraConflictError` | Concurrent checkpoint writers | Re-read state and retry — the saver handles this automatically during graph execution |
