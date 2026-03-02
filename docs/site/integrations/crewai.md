# CrewAI Integration

Use Mnemora as the storage backend for CrewAI agents.

## Prerequisites

- A Mnemora API key
- CrewAI installed

## Install

```bash
pip install "mnemora[crewai]"
```

This installs `mnemora` and `crewai`.

## How it works

`MnemoraCrewStorage` implements CrewAI's `Storage` interface. It maps each CrewAI storage key to a Mnemora `session_id` under a fixed `agent_id`, storing values as working memory in DynamoDB.

| CrewAI concept | Mnemora concept |
|----------------|-----------------|
| Storage key | `session_id` |
| Storage value | Working memory `data` dict |
| `agent_id` param | Namespace for all keys on this storage instance |

`MnemoraCrewStorage` only accepts `MnemoraSync` because CrewAI is synchronous.

## Basic usage

```python
from mnemora import MnemoraSync
from mnemora.integrations.crewai import MnemoraCrewStorage

client = MnemoraSync(api_key="mnm_...")
storage = MnemoraCrewStorage(client=client, agent_id="crew-researcher")

# Save
storage.save("research-plan", {"steps": ["search", "read", "summarize"]})

# Load
plan = storage.load("research-plan")
print(plan)
# {'steps': ['search', 'read', 'summarize']}

# List all keys
keys = storage.list_keys()
print(keys)
# ['research-plan']

# Delete
storage.delete("research-plan")

# Reset (delete all keys)
storage.reset()
```

## Use with a CrewAI Agent

Wire `MnemoraCrewStorage` into a CrewAI agent by passing it where CrewAI expects a storage backend.

```python
from crewai import Agent, Task, Crew
from mnemora import MnemoraSync
from mnemora.integrations.crewai import MnemoraCrewStorage

client = MnemoraSync(api_key="mnm_...")
storage = MnemoraCrewStorage(client=client, agent_id="research-crew")

researcher = Agent(
    role="Research Analyst",
    goal="Find and summarize information on a topic",
    backstory="You are an expert at gathering and distilling information.",
    memory=True,
    # CrewAI uses the storage backend for its memory layer
)

task = Task(
    description="Research the impact of vector databases on AI agent performance.",
    expected_output="A concise 3-paragraph summary.",
    agent=researcher,
)

crew = Crew(agents=[researcher], tasks=[task])

# Manually save intermediate results to Mnemora
storage.save("topic", {"name": "vector databases in AI agents"})

result = crew.kickoff()
print(result)

# Save the final result for later retrieval
storage.save("final-report", {"content": str(result)})
```

## Value types

Values can be any JSON-serialisable type. Dict values are stored directly. Non-dict values (strings, numbers, lists) are wrapped in `{"value": ...}`.

```python
storage.save("count", 42)
data = storage.load("count")
print(data)  # {"value": 42}
print(data["value"])  # 42

storage.save("tags", ["research", "ai"])
data = storage.load("tags")
print(data)  # {"value": ["research", "ai"]}

storage.save("config", {"timeout": 30, "retries": 3})
data = storage.load("config")
print(data)  # {"timeout": 30, "retries": 3}  — stored directly, no wrapping
```

## search method

`search()` accepts a query string for interface compatibility with CrewAI, but performs a full scan rather than a text search. Working memory does not support free-text search. For text similarity search, use `client.search_memory()` (semantic memory).

```python
# Returns all stored values regardless of query
all_values = storage.search("any query string")
for value in all_values:
    print(value)
```

## Isolating multiple crews

Use a different `agent_id` for each crew to keep their storage keys separate.

```python
from mnemora import MnemoraSync
from mnemora.integrations.crewai import MnemoraCrewStorage

client = MnemoraSync(api_key="mnm_...")

research_storage = MnemoraCrewStorage(client=client, agent_id="crew-research")
writing_storage = MnemoraCrewStorage(client=client, agent_id="crew-writing")

research_storage.save("findings", {"sources": 12, "pages_read": 47})
writing_storage.save("draft", {"word_count": 800, "status": "in-progress"})

# Each storage instance sees only its own keys
print(research_storage.list_keys())  # ['findings']
print(writing_storage.list_keys())   # ['draft']
```

## Error handling

```python
from mnemora import MnemoraAuthError, MnemoraError
from mnemora.integrations.crewai import MnemoraCrewStorage

try:
    storage.save("plan", {"step": 1})
except MnemoraAuthError:
    print("API key is invalid or revoked.")
except MnemoraError as e:
    print(f"API error {e.code}: {e.message}")
```

`load()` returns `None` when a key does not exist — it does not raise `MnemoraNotFoundError`.
`delete()` is idempotent — deleting a non-existent key is a no-op.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `load()` returns `None` | Key was never saved or was deleted | Check `list_keys()` to see what exists |
| Scalar value wrapped in `{"value": ...}` | Non-dict values are automatically wrapped | Access `data["value"]` to get the original value |
| `reset()` did not delete all keys | Keys were added concurrently during reset | Call `reset()` again — it is safe to call multiple times |
| `MnemoraAuthError` on first call | Invalid API key | Verify your key in the dashboard |
