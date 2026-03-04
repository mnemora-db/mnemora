<p align="center">
  <img src="https://mnemora.dev/icon.svg" alt="Mnemora" width="48" height="48" />
</p>

<h1 align="center">mnemora</h1>

<p align="center"><strong>Open-source serverless memory database for AI agents</strong></p>

<p align="center">
  <a href="https://pypi.org/project/mnemora/"><img src="https://img.shields.io/pypi/v/mnemora?color=2DD4BF&label=PyPI" alt="PyPI" /></a>
  <a href="https://github.com/mnemora-db/mnemora/stargazers"><img src="https://img.shields.io/github/stars/mnemora-db/mnemora?style=flat&color=2DD4BF" alt="GitHub stars" /></a>
  <a href="https://github.com/mnemora-db/mnemora/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT%20%2F%20BSL--1.1-blue" alt="License" /></a>
  <img src="https://img.shields.io/badge/build-passing-brightgreen" alt="Build" />
  <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python 3.9+" />
</p>

<p align="center">
  4 memory types. One API. Sub-10ms reads. No LLM in your CRUD path.
</p>

<p align="center">
  <a href="https://mnemora.dev">Website</a> &middot;
  <a href="https://mnemora.dev/docs/quickstart">Docs</a> &middot;
  <a href="https://mnemora.dev/blog">Blog</a> &middot;
  <a href="https://pypi.org/project/mnemora/">PyPI</a>
</p>

---

## Quick Start

```bash
pip install mnemora
```

```python
from mnemora import MnemoraSync

client = MnemoraSync(api_key="mnm_...")

# Working memory — sub-10ms key-value state
client.store_state("my-agent", {"task": "research", "step": 1})

# Semantic memory — auto-embedded, vector-searchable
client.store_memory("my-agent", "User prefers concise replies")

# Search across memories
results = client.search_memory("user preferences", agent_id="my-agent")
for r in results:
    print(r.content, r.similarity_score)
```

Get your API key at [mnemora.dev/dashboard](https://mnemora.dev/dashboard) or [self-host](#self-hosting) in one command.

---

## Why Mnemora

| Feature | Mnemora | Mem0 | Zep | Letta |
|---|---|---|---|---|
| Memory types | 4 (state, semantic, episodic, procedural) | 1 (semantic) | 2 (semantic + temporal) | 2 (core + archival) |
| LLM required for CRUD | **No** | Every operation | No | Every operation |
| Serverless | **Fully** | Cloud only | Cloud only | Server required |
| Self-hostable | **`cdk deploy`** | No | Partial | Yes |
| State latency | **<10ms** | ~500ms | <200ms | ~1s |
| Multi-tenant | **Built-in** | No | Yes | No |
| LangGraph checkpoints | **Native** | No | No | No |
| Framework integrations | LangGraph, LangChain, CrewAI | LangChain | LangChain | LangChain |

---

## Memory Types

### Working Memory

Key-value state in DynamoDB. Sub-10ms reads with optimistic locking and configurable TTL.

```python
client.store_state("agent-1", {"plan": ["step-1", "step-2"]}, ttl_hours=24)
current = client.get_state("agent-1")
```

### Semantic Memory

Natural-language text auto-embedded as 1024-dimensional vectors via Bedrock Titan. Stored in Aurora pgvector. Duplicates (cosine similarity > 0.95) are merged, not re-inserted.

```python
client.store_memory("agent-1", "User's timezone is UTC+9.", namespace="profile")
results = client.search_memory("what timezone?", agent_id="agent-1", top_k=5)
```

### Episodic Memory

Append-only time-series event log. Hot data in DynamoDB, cold data in S3. Supports session replay and time-range queries.

```python
client.store_episode("agent-1", "sess-42", type="tool_call",
    content={"tool": "web_search", "query": "latest GDP data"})
history = client.get_session_episodes("agent-1", "sess-42")
```

### Procedural Memory

Tool definitions, schemas, prompt templates, and rules in Postgres. Version-controlled and queryable by name.

> Schema is live. SDK methods ship in v0.2.

---

## Integrations

### LangGraph CheckpointSaver

```python
from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver

client = MnemoraClient(api_key="mnm_...")
saver = MnemoraCheckpointSaver(client=client, namespace="langgraph")

graph = StateGraph(...)
app = graph.compile(checkpointer=saver)
```

`pip install "mnemora[langgraph]"`

### LangChain Memory

```python
from mnemora import MnemoraSync
from mnemora.integrations.langchain import MnemoraMemory

client = MnemoraSync(api_key="mnm_...")
memory = MnemoraMemory(client=client, agent_id="my-agent", session_id="sess-1")
```

`pip install "mnemora[langchain]"`

### CrewAI Storage

```python
from mnemora import MnemoraSync
from mnemora.integrations.crewai import MnemoraCrewStorage

client = MnemoraSync(api_key="mnm_...")
storage = MnemoraCrewStorage(client=client, agent_id="crewai-agent")
storage.save("plan", {"steps": ["gather", "analyze", "write"]})
```

`pip install "mnemora[crewai]"`

---

## Self-Hosting

Deploy the entire stack to your own AWS account:

```bash
git clone https://github.com/mnemora-db/mnemora.git
cd mnemora/infra && npm install && npx cdk deploy
```

Provisions DynamoDB, Aurora Serverless v2 (pgvector), Lambda (ARM64), HTTP API Gateway, S3, and CloudWatch. Estimated idle cost: ~$15/month. Aurora scales to zero when not in use.

---

## Architecture

```
SDK (Python) → HTTP API Gateway → Lambda (ARM64, Python 3.12)
                                    ├── DynamoDB      (working memory + episodes hot tier)
                                    ├── Aurora pgvector (semantic memory + procedural)
                                    ├── S3             (episodes cold tier)
                                    └── Bedrock Titan  (embeddings, 1024d)
```

All infrastructure is serverless and multi-tenant. API keys are SHA-256 hashed. Tenant isolation is enforced at every layer (DynamoDB partition keys, Aurora parameterized queries, S3 prefixes).

---

## Links

- **Website:** [mnemora.dev](https://mnemora.dev)
- **Documentation:** [mnemora.dev/docs/quickstart](https://mnemora.dev/docs/quickstart)
- **Blog:** [mnemora.dev/blog](https://mnemora.dev/blog)
- **Dashboard:** [mnemora.dev/dashboard](https://mnemora.dev/dashboard)
- **PyPI:** [pypi.org/project/mnemora](https://pypi.org/project/mnemora/)

---

## Contributing

PRs welcome. Before submitting:

```bash
cd api && ruff check . && ruff format .    # Python lint
cd sdk && python -m pytest tests/ -v       # SDK tests
cd infra && npx tsc --noEmit               # TypeScript check
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

| Directory | License |
|---|---|
| `sdk/` | [MIT](sdk/LICENSE) |
| `dashboard/` | [MIT](dashboard/LICENSE) |
| `infra/`, `api/` | [BSL 1.1](LICENSE) |
