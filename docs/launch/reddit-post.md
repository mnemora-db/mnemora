# Reddit Posts

---

## Variant 1: r/MachineLearning

**Title:** We built a unified memory layer for AI agents — one API for working, semantic, episodic, and procedural memory (open source, AWS-native)

**Word count:** 647

---

Agent memory is an infrastructure problem that keeps getting solved badly. The standard approach is to bolt together a key-value store for session state, a vector database for semantic recall, an append-only log for event history, and a relational store for tool definitions. You end up with 3-5 separate databases, inconsistent data models, and no unified query interface. Every new agent project rediscovers this complexity.

We spent the past few months building Mnemora to address this directly. Here is what it is and the architectural decisions behind it.

**What it does**

A single REST API that routes to four storage backends, each chosen for the access pattern it serves:

- **Working memory** (DynamoDB, on-demand mode): Key-value state per agent and session. Optimistic locking via a version integer stored with every item. Native DynamoDB TTL for automatic expiry. Warm read latency is approximately 150ms round-trip including HTTP API Gateway overhead.

- **Semantic memory** (Aurora Serverless v2 + pgvector): Text is auto-embedded at write time using Amazon Bedrock Titan Text Embeddings v2 (`amazon.titan-embed-text-v2:0`, 1024 dimensions, `normalize=True`). Vectors are indexed with HNSW (m=16, ef_construction=200) using cosine distance. Before inserting a new record, we check for an existing entry with cosine similarity above 0.95 for the same tenant and agent — if found, we update in place and merge metadata rather than creating a duplicate. Store latency is 3-4 seconds on warm Lambdas because it includes the Bedrock API call. Cold starts take approximately 7 seconds due to VPC networking and Aurora resume time.

- **Episodic memory** (DynamoDB + S3): Append-only time-series logs partitioned by tenant and agent. Recent episodes stay in DynamoDB; older episodes are tiered to S3. The API supports ISO 8601 time-range queries, event-type filtering, and full session replay.

- **Procedural memory** (Postgres): Schema for tool definitions, schemas, prompts, and rules is deployed. SDK methods are targeting v0.2.

**Architecture choices worth explaining**

We use HTTP API Gateway rather than REST API Gateway. At $1 per million requests versus $3.50, it is a meaningful cost difference for an open-source project where users self-host. Lambda runs on ARM64/Graviton2 for similar cost reasons.

Tenant isolation is logical rather than physical: DynamoDB uses a `{tenant_id}#{agent_id}` partition key prefix; Aurora uses a `tenant_id` column with parameterized queries and row-level security as a defense-in-depth layer; S3 uses a `{tenant_id}/` key prefix. API key to tenant_id mapping is enforced in the Lambda authorizer — client-provided tenant values are never trusted.

We chose Aurora Serverless v2 over a dedicated vector database for semantic memory because it gives us relational queries and vector search in the same engine. The trade-off is cold start latency when Aurora scales down to zero ACUs. For workloads that need sub-second semantic search consistently, you would want to keep Aurora at a minimum of 0.5 ACUs, which changes the cost profile.

**How it compares architecturally**

Mem0 requires an LLM call for each write operation to extract and structure memories (~500ms added per operation). Mnemora embeds directly — no extraction layer. Letta/MemGPT similarly requires an LLM for memory management. Zep/Graphiti uses a temporal knowledge graph, which is a different data model suited to entity-relationship reasoning; their platform is not fully self-hostable. Our approach trades graph traversal capability for simpler deployment and no mandatory LLM dependency.

**Numbers from integration tests**

- State store (warm Lambda): ~150ms round-trip
- Semantic store (embed + Aurora insert): ~3-4s
- GET across all three stores: 42-63ms server-side
- Cross-memory search: 134ms server-side
- GDPR purge (DynamoDB + Aurora + S3): 836ms
- Estimated idle cost self-hosted: ~$15/month

**Getting started**

```bash
pip install mnemora
```

Deploy the infrastructure:

```bash
git clone https://github.com/mnemora-dev/mnemora
cd mnemora/infra && npx cdk deploy
```

446 tests passing (330 API + 116 SDK). MIT license for the SDK, BSL 1.1 for the infrastructure stack.

Interested in feedback on the storage tier choices, the deduplication approach, and whether the LangGraph integration covers the checkpoint use cases people actually need.

---

## Variant 2: r/LangChain

**Title:** Mnemora — persistent memory for LangGraph and LangChain agents, self-hosted on AWS (open source)

**Word count:** 573

---

If you have built a LangGraph agent and hit the point where you need graph state to survive across process restarts, you have probably already looked at `langgraph-checkpoint-postgres`. It works, but it gives you checkpoint storage only — you still need to separately handle semantic recall, conversation history, and any structured data your agent needs to remember.

Mnemora is a unified memory API that covers all four layers, with native LangGraph and LangChain integrations built in.

**The LangGraph integration**

`MnemoraCheckpointSaver` extends `BaseCheckpointSaver` and implements the full async interface: `aget`, `aget_tuple`, `aput`, `aput_writes`, and `alist`. Synchronous shims (`get_tuple`, `put`, `put_writes`, `list`) are available for non-async contexts.

LangGraph `thread_id` maps to a Mnemora `agent_id`. Checkpoint namespace maps to `session_id`. Optimistic locking is forwarded transparently — the Mnemora version integer travels in the returned `RunnableConfig` so concurrent writers get a `MnemoraConflictError` instead of silent data loss.

```python
from mnemora import MnemoraClient
from mnemora.integrations.langgraph import MnemoraCheckpointSaver

client = MnemoraClient(api_key="mnm_...")
saver = MnemoraCheckpointSaver(client=client)

# Drop into any existing LangGraph app
from langgraph.graph import StateGraph
graph = StateGraph(...)
app = graph.compile(checkpointer=saver)

result = await app.ainvoke(
    {"messages": [...]},
    config={"configurable": {"thread_id": "abc123"}},
)
```

Install with the optional dependency:

```bash
pip install "mnemora[langgraph]"
```

**The LangChain integration**

`MnemoraMemory` extends `BaseChatMessageHistory`. Each message is stored as a `"conversation"` episode in episodic memory, which means it is also queryable by time range and composable with action logs from the same session.

```python
from mnemora import MnemoraSync
from mnemora.integrations.langchain import MnemoraMemory
from langchain_core.runnables.history import RunnableWithMessageHistory

client = MnemoraSync(api_key="mnm_...")

chain_with_history = RunnableWithMessageHistory(
    chain,
    lambda session_id: MnemoraMemory(
        client=client,
        agent_id="agent-1",
        session_id=session_id,
    ),
)
```

**What else the API covers**

Beyond checkpoints and message history, the same API gives you:

- `client.store_memory(agent_id, "User prefers bullet points")` — auto-embedded, vector-searchable via pgvector
- `client.search_memory("formatting preferences", agent_id="agent-1")` — cosine similarity search, returns top-K results above threshold
- `client.store_episode(agent_id, session_id, "action", {"tool": "web_search", "query": "..."})` — append to time-series log
- `client.search_all(query, agent_id)` — cross-memory search (semantic + episodic text match, 134ms server-side)
- `client.purge_agent(agent_id)` — GDPR deletion across all stores (DynamoDB + Aurora + S3, ~836ms)

**Self-hosting**

The stack is AWS CDK. Deploy with:

```bash
cd infra && npx cdk deploy
```

DynamoDB + Aurora Serverless v2 + S3 + Lambda (ARM64) + HTTP API Gateway. Estimated idle cost: ~$15/month.

One honest caveat: semantic store latency is 3-4 seconds on warm invocations because it includes a Bedrock Titan embedding call. Cold starts are approximately 7 seconds. If you need sub-second semantic writes, this is the right trade-off to understand before adopting.

446 tests passing. MIT license for the SDK (BSL 1.1 for the infrastructure CDK code).

```bash
pip install "mnemora[langgraph]"   # LangGraph integration
pip install "mnemora[langchain]"   # LangChain integration
pip install "mnemora[all]"         # Everything
```

GitHub: https://github.com/mnemora-dev/mnemora
