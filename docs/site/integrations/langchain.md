# LangChain Integration

Persist chat message history in Mnemora episodic memory so conversations survive process restarts.

## Prerequisites

- A Mnemora API key
- LangChain 0.2+ (`langchain-core`)

## Install

```bash
pip install "mnemora[langchain]"
```

This installs `mnemora` and `langchain-core`.

## How it works

`MnemoraMemory` extends LangChain's `BaseChatMessageHistory`. Each message is stored as an episodic memory episode of type `"conversation"` under the configured `agent_id` / `session_id` pair.

- `add_message` writes one episode via `POST /v1/memory/episodic`
- The `messages` property reads all episodes for the session via `GET /v1/memory/episodic/{agent_id}/sessions/{session_id}` and deserialises them back into LangChain `BaseMessage` objects

Messages survive across process restarts because they are persisted in DynamoDB.

## Basic usage

```python
from mnemora import MnemoraSync
from mnemora.integrations.langchain import MnemoraMemory

client = MnemoraSync(api_key="mnm_...")
memory = MnemoraMemory(client=client, agent_id="my-agent", session_id="sess-1")

# Add messages
memory.add_user_message("What is the capital of France?")
memory.add_ai_message("The capital of France is Paris.")

# Retrieve all messages in chronological order
for msg in memory.messages:
    print(type(msg).__name__, ":", msg.content)
```

**Output:**

```
HumanMessage : What is the capital of France?
AIMessage : The capital of France is Paris.
```

## Use with RunnableWithMessageHistory

Wire `MnemoraMemory` into any LCEL chain that accepts a history provider.

```python
from mnemora import MnemoraSync
from mnemora.integrations.langchain import MnemoraMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory

client = MnemoraSync(api_key="mnm_...")

llm = ChatOpenAI(model="gpt-4o-mini")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}"),
])

chain = prompt | llm

chain_with_history = RunnableWithMessageHistory(
    chain,
    # Factory function: called once per session_id
    lambda session_id: MnemoraMemory(
        client=client,
        agent_id="support-agent",
        session_id=session_id,
    ),
    input_messages_key="question",
    history_messages_key="history",
)

# First call — no history yet
response = chain_with_history.invoke(
    {"question": "My order ID is 12345."},
    config={"configurable": {"session_id": "user-alice"}},
)
print(response.content)

# Second call — history is loaded from Mnemora automatically
response = chain_with_history.invoke(
    {"question": "What was my order ID?"},
    config={"configurable": {"session_id": "user-alice"}},
)
print(response.content)
# Output: Your order ID is 12345.
```

## Multiple sessions per agent

Each `session_id` is an independent conversation. Pass a different `session_id` to separate conversations under the same `agent_id`.

```python
from mnemora import MnemoraSync
from mnemora.integrations.langchain import MnemoraMemory

client = MnemoraSync(api_key="mnm_...")

alice_memory = MnemoraMemory(client=client, agent_id="support-agent", session_id="alice")
bob_memory = MnemoraMemory(client=client, agent_id="support-agent", session_id="bob")

alice_memory.add_user_message("I need help with billing.")
bob_memory.add_user_message("I need help with shipping.")

# Each session is isolated
print(len(alice_memory.messages))  # 1
print(len(bob_memory.messages))    # 1
```

## Clear a session

`clear()` issues a GDPR purge that deletes all memory (working, semantic, and episodic) for the configured `agent_id`. Use it only when you intend to remove all agent data, not just a single session.

```python
memory.clear()
```

To delete only specific episodic records, use `client.delete_state()` or call the API directly.

## add_message vs add_user_message / add_ai_message

| Method | Argument | Use when |
|--------|----------|----------|
| `add_user_message(text)` | Plain string | Storing a human turn |
| `add_ai_message(text)` | Plain string | Storing an AI turn |
| `add_message(msg)` | `BaseMessage` instance | Storing any LangChain message type including `SystemMessage`, `FunctionMessage`, etc. |

## Error handling

```python
from mnemora import MnemoraAuthError, MnemoraError
from mnemora.integrations.langchain import MnemoraMemory

try:
    for msg in memory.messages:
        print(msg.content)
except MnemoraAuthError:
    print("API key is invalid or revoked.")
except MnemoraError as e:
    print(f"API error {e.code}: {e.message}")
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportError: langchain-core is required` | Package not installed | Run `pip install "mnemora[langchain]"` |
| Messages are empty on second run | Wrong `session_id` | Use a stable, deterministic `session_id` per conversation |
| `clear()` deleted more than expected | Purges all agent data | Use a dedicated `agent_id` per user if isolation is required |
| `RuntimeError` on `messages` | Passing async client without `sync=False` | Pass `sync=False` or use `MnemoraSync` |
