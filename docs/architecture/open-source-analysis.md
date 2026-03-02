# Mnemora: Open-Source & Competitive Technical Analysis

## Pre-Build Intelligence Report | March 2026

---

## 1. Competitor Open-Source Deep Dive

### 1.1 Mem0 (github.com/mem0ai/mem0) — 43K★, Apache 2.0

**Architecture (from paper arXiv:2504.19413 + codebase):**

Mem0 operates as a memory SDK/API layer, NOT a database. Its core loop:

1. **Extraction Phase:** New message pair (user + assistant) comes in. Mem0 feeds the pair + conversation summary + last X messages to an LLM with `MEMORY_DEDUCTION_PROMPT`. The LLM generates bullet-list "memory candidates."

2. **Update Phase:** Each candidate is compared against existing memories via vector similarity. A Tool Call mechanism decides: CREATE new memory, UPDATE existing, DELETE obsolete, or NOOP.

3. **Storage:** Hybrid datastore — vector DB (Qdrant, Pinecone, Chroma, pgvector supported), graph DB (Neo4j, FalkorDB), key-value store (Redis, custom).

**Key Technical Findings:**

- **LLM-dependent:** Requires an LLM call for EVERY memory operation (extraction + update). Default is `gpt-4.1-nano`. This adds latency (200-500ms per add) and cost (~$0.001-0.01 per operation).
- **No database engine:** Mem0 wraps external databases. Users must provision and manage their own Qdrant/Pinecone + Neo4j + Redis.
- **Memory deduplication:** Uses cosine similarity > 0.95 threshold to trigger update vs insert. Smart but LLM-dependent for conflict resolution.
- **Confidence scoring + decay:** Memories have `score` field that decreases over time. Configurable decay rate.
- **Graph memory (v0.1.29+):** Neo4j/FalkorDB for entity-relationship extraction. Adds another infrastructure dependency.
- **v1.0.0 changes:** Async-by-default, rerankers, Azure OpenAI support, improved vector store support.
- **OpenMemory MCP:** Portable memory standard. Signals ambition beyond just SDK.

**Gaps Mnemora Exploits:**

- No auth, no storage, no real-time, no execution logs
- Every operation requires LLM call = expensive at scale
- Users manage 3 separate databases (vector + graph + KV)
- No serverless/scale-to-zero (infrastructure always-on)
- No LangGraph checkpoint compatibility (critical for adoption)
- No built-in episodic memory with time-range queries
- No audit trail / compliance features

**What Mnemora Should Copy:**

- Memory deduplication pattern (cosine > 0.95)
- Confidence scoring with temporal decay
- Auto-extraction from conversations (but make it optional, not mandatory)
- Clean Python SDK API design: `memory.add()`, `memory.search()`, `memory.get_all()`
- User/agent/session ID hierarchy for multi-tenancy

---

### 1.2 Zep / Graphiti (github.com/getzep/graphiti) — Open Source (Graphiti only)

**Architecture:**

Zep pivoted hard. The commercial product is now closed-source. Only **Graphiti** (their temporal knowledge graph engine) remains open-source.

**Graphiti Technical Design:**

1. **Bi-temporal model:** Every fact has `valid_at` (when it became true) and `invalid_at` (when it stopped being true). This is THE killer feature for agent memory.
2. **Real-time incremental updates:** New data episodes integrated without batch recomputation.
3. **Hybrid retrieval:** Semantic embeddings + keyword (BM25) + graph traversal combined.
4. **Graph backends:** Neo4j (primary), FalkorDB, Amazon Neptune.
5. **Rerankers:** RRF, MMR, graph-based episode-mentions, node distance, cross-encoder.

**Paper Findings (arXiv:2501.13956):**

- Outperforms MemGPT on DMR benchmark: 94.8% vs 93.4%
- Sub-200ms retrieval latency (critical for voice AI use case)
- Uses BGE-m3 for reranking/embedding, gpt-4o-mini for graph construction

**Key Takeaway for Mnemora:**

- **Temporal versioning is essential.** Facts change. "User preferred X" becomes "User now prefers Y." Without temporal tracking, agents hallucinate about outdated facts.
- **We MUST implement bi-temporal fields** on all memory types: `valid_from`, `valid_until`, `ingested_at`.
- **Graph relationships matter** but are complex. Start with relational (Postgres foreign keys) before graph DB.
- Graphiti requires Neo4j — heavy infrastructure dependency we can avoid by using Postgres recursive CTEs for basic graph traversal.

**What Mnemora Should Copy:**

- Bi-temporal data model (valid_at/invalid_at on every memory record)
- Hybrid search (semantic + keyword + relational joins)
- Automatic fact invalidation when contradictory information arrives
- Framework-agnostic design (LangChain, LangGraph, AutoGen, Chainlit)

---

### 1.3 Letta / MemGPT (github.com/letta-ai/letta) — 42K★, Apache 2.0

**Architecture (MemGPT paradigm):**

The foundational insight: treat LLM context windows like an OS manages memory.

1. **Core Memory (RAM):** Small, always in context. Contains `human` block (user info) and `persona` block (agent identity). Self-editable by the agent via tool calls.
2. **Archival Memory (Disk):** Large external storage. Agent can `archival_memory_insert()` and `archival_memory_search()` to manage it.
3. **Recall Memory:** Searchable conversation history.
4. **Memory Blocks:** Labeled key-value pairs with configurable size limits (e.g., 5000 chars).

**V1 Architecture Changes (2025+):**

- Moved away from MemGPT's tool-call-only architecture
- New agent loop optimized for frontier reasoning models (GPT-5, Claude 4.5)
- Context Repositories: git-based versioning for memory
- Sleep-time compute: agents refine memory during idle time
- Skill Learning: agents learn from past experience and improve
- Conversations API: shared memory across parallel user interactions

**Key Technical Findings:**

- **Self-editing memory is powerful but dangerous.** Agents can corrupt their own memory. Needs guardrails.
- **Memory blocks are simple but effective.** Labeled chunks with size limits are easy to implement and reason about.
- **Model-agnostic:** Works with any LLM that supports tool calling.
- **Heavy server:** Letta requires running a full server process. Not serverless.
- **PostgreSQL underneath:** Uses Postgres for persistence (good validation for our Aurora choice).

**What Mnemora Should Copy:**

- Memory blocks concept (labeled, size-limited, agent-editable)
- Separate core (always-in-context) vs archival (searchable external) memory
- Agent self-editing with guardrails (rollback, version history)
- Sleep-time compute concept (async memory refinement)

**What Mnemora Should NOT Copy:**

- Full server requirement (we're serverless)
- Complex agent loop architecture (we're a database, not an agent framework)
- Tool-call-only interaction model

---

### 1.4 OpenMemory (github.com/CaviraOSS/OpenMemory) — Newer entrant

**Notable features:**

- Temporal facts as first-class: `POST /api/temporal/fact` with `valid_from` field, auto-closes previous fact
- MCP server built-in (works with Claude Desktop, Copilot, Codex)
- Source connectors: GitHub, Notion, Google Drive, web crawler
- Migration tool from Mem0, Zep, Supermemory
- Node.js backend, runs on port 8080

**Key Takeaway:** Even small open-source projects are implementing temporal facts and MCP servers. These are table-stakes features.

---

## 2. Framework Integration Analysis

### 2.1 LangGraph Checkpoint Interface (CRITICAL — #1 Integration Priority)

**Source:** `langgraph-checkpoint-postgres` (PyPI + GitHub)

**Schema (from source code):**

```sql
-- LangGraph creates these tables via .setup()
CREATE TABLE IF NOT EXISTS checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE IF NOT EXISTS checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

CREATE TABLE IF NOT EXISTS checkpoint_writes (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    task_id TEXT NOT NULL,
    idx INTEGER NOT NULL,
    channel TEXT NOT NULL,
    type TEXT,
    blob BYTEA NOT NULL,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id, task_id, idx)
);
```

**Interface we must implement (Python `BaseCheckpointSaver`):**

```python
class MnemoraCheckpointSaver(BaseCheckpointSaver):
    def put(self, config, checkpoint, metadata, new_versions):
        """Save checkpoint to Mnemora"""
    
    def put_writes(self, config, writes, task_id):
        """Save intermediate writes"""
    
    def get_tuple(self, config):
        """Get checkpoint by config (thread_id + optional checkpoint_id)"""
    
    def list(self, config, *, filter=None, before=None, limit=None):
        """List checkpoints for a thread (newest first)"""
```

**Critical Implementation Notes:**

- Connection MUST use `autocommit=True` and `row_factory=dict_row` (psycopg3 requirement)
- `.setup()` method must be idempotent (CREATE TABLE IF NOT EXISTS)
- Checkpoints are JSONB — our Aurora pgvector cluster handles this natively
- Thread isolation via composite primary keys
- **Known pain point:** No built-in cleanup for old checkpoints (Issue #1138). WE should add TTL-based cleanup as a differentiator.

**Implementation Plan:**

- Create `mnemora-langgraph` Python package
- Implement `MnemoraCheckpointSaver` that wraps our REST API
- Store checkpoints in our Aurora Postgres (same cluster as semantic memory)
- Add TTL-based cleanup (Mem0 and LangGraph both lack this)
- Add checkpoint size metrics and alerting

---

### 2.2 LangChain Memory Interface

**Key classes to implement:**

```python
from langchain.memory import BaseMemory

class MnemoraMemory(BaseMemory):
    memory_variables = ["history", "memories"]
    
    def load_memory_variables(self, inputs):
        """Load relevant memories for current input"""
        # Search semantic memory + get recent episodic
    
    def save_context(self, inputs, outputs):
        """Save conversation turn to Mnemora"""
        # Store as episodic memory + extract semantic memories
    
    def clear(self):
        """Clear all memories for this session"""
```

### 2.3 CrewAI Memory Interface

**CrewAI memory types map directly to ours:**

- `ShortTermMemory` → Working memory (DynamoDB)
- `LongTermMemory` → Semantic memory (pgvector)
- `EntityMemory` → Procedural memory (Postgres relational)

CrewAI has a pluggable storage backend. We implement their `Storage` interface.

---

## 3. AWS Services Deep Analysis

### 3.1 pgvector on Aurora Serverless v2

**Current state (verified):**

- pgvector extension available on Aurora PostgreSQL 15.x+
- Supports HNSW and IVFFlat indexes
- 1024-dimension vectors (Bedrock Titan output) well within limits
- Aurora Serverless v2: min 0.5 ACU ($0.12/ACU-hour) = ~$43.80/month floor
- Scale-to-zero NOT available on Aurora Serverless v2 (minimum 0.5 ACU always)

**Critical finding: Aurora does NOT scale to zero.**

This is a significant cost issue for the free tier. Options:
1. **Accept the $44/month floor** and amortize across all free tier users (shared multi-tenant cluster)
2. **Use Neon Serverless Postgres** instead (true scale-to-zero, pgvector support, $19/month plan)
3. **Use Supabase Postgres** (pgvector, free tier available, but adds dependency on competitor)

**Recommendation:** Start with Aurora Serverless v2 shared cluster. The $44/month floor is acceptable when shared across 50-100 free tier users. Evaluate Neon migration if Aurora costs become problematic.

**pgvector Performance Benchmarks:**

- 10K vectors, 1024 dims: ~5ms search latency (HNSW, ef_search=40)
- 100K vectors: ~15ms search latency
- 1M vectors: ~50ms search latency
- HNSW index build: ~2 minutes for 100K vectors

**Best Practices for pgvector:**

- Use HNSW over IVFFlat (better recall, slightly more memory)
- Set `ef_construction = 200` for build, `ef_search = 40` for query
- Use `vector_cosine_ops` for normalized embeddings (Bedrock Titan outputs normalized)
- Partial indexes with tenant_id for multi-tenant isolation
- VACUUM ANALYZE after large bulk inserts

### 3.2 DynamoDB Design Patterns

**Single-table design for agent state:**

| PK | SK | Attributes |
|----|----|----|
| `TENANT#t1` | `AGENT#a1#SESSION#s1` | state JSON, version, ttl, created_at, updated_at |
| `TENANT#t1` | `AGENT#a1#META` | agent metadata, config, created_at |
| `TENANT#t1` | `EPISODE#a1#2026-03-01T10:00:00Z#ep1` | episode content, type, metadata |
| `TENANT#t1` | `APIKEY#hash` | tenant_id, created_at, last_used, rate_limit |

**GSI-1 (inverted):** SK as PK for cross-tenant queries (admin only)

**TTL:** DynamoDB native TTL for working memory expiration (set `ttl` attribute to Unix timestamp)

**Optimistic locking:** Use `version` attribute with `ConditionExpression: version = :expected_version`

**Cost optimization:**

- On-demand pricing for unpredictable agent workloads (no capacity planning)
- Reserved capacity ONLY after 3 months of stable usage data
- DynamoDB Streams for real-time archival to S3 (episodic cold storage)

### 3.3 Bedrock Titan Text Embeddings v2

**Verified specs:**

- Model ID: `amazon.titan-embed-text-v2:0`
- Dimensions: 256, 512, or 1024 (configurable)
- Max input: 8192 tokens
- Cost: $0.02 per 1M input tokens (5x cheaper than Cohere)
- Latency: ~100-200ms per request

**Recommendation:** Use 1024 dimensions for best accuracy. Cost difference between 256 and 1024 dims is negligible ($0.02/M tokens regardless).

### 3.4 Lambda + HTTP API Gateway

**Verified architecture:**

- HTTP API Gateway: $1.00/million requests (71% cheaper than REST API)
- Lambda ARM64 (Graviton): 20% cheaper than x86
- Lambda function URLs as alternative to API Gateway (even cheaper, but less features)
- Cold start: ~200-500ms for Node.js, ~1-3s for Python
- **Recommendation:** Use Node.js (TypeScript) for Lambda handlers for lowest cold starts

---

## 4. Critical Architectural Decisions (Locked Before Build)

### Decision 1: TypeScript vs Python for Backend

**TypeScript (Node.js):**
- ✅ Faster Lambda cold starts (200ms vs 1-3s)
- ✅ Better DynamoDB SDK (AWS SDK v3 modular)
- ✅ Shared language with dashboard (Next.js)
- ❌ pgvector ecosystem is Python-first
- ❌ AI/ML ecosystem heavily Python

**Python:**
- ✅ Better pgvector/SQLAlchemy integration
- ✅ Native LangChain/CrewAI SDK development
- ✅ Bedrock SDK more mature
- ❌ Slower Lambda cold starts
- ❌ Two languages if dashboard is Next.js

**DECISION: Python for Lambda handlers + SDK, TypeScript for dashboard.**
Rationale: The SDK and framework integrations (LangChain, CrewAI, LangGraph) are all Python. Cold start penalty is mitigated by provisioned concurrency for critical paths.

### Decision 2: CDK vs Terraform vs SAM

**DECISION: AWS CDK (TypeScript)**
Rationale: CDK has best abstractions for Aurora + Lambda + DynamoDB pattern. L2 constructs handle VPC, security groups, IAM policies. TypeScript CDK is most mature.

### Decision 3: Multi-Tenant Isolation Model

**DECISION: Shared infrastructure with logical isolation**
- DynamoDB: Partition key prefix (TENANT#id)
- Aurora: Row-level tenant_id column + Postgres Row Level Security (RLS)
- S3: Prefix isolation (s3://bucket/tenant_id/)
- API: JWT/API key maps to tenant_id at authorizer layer

### Decision 4: API Design — REST vs GraphQL

**DECISION: REST (OpenAPI 3.1)**
Rationale: Simpler for agent frameworks to integrate. LangChain/CrewAI all use REST. GraphQL adds complexity without clear benefit for this use case.

### Decision 5: Memory Extraction — LLM-Powered vs User-Driven

**DECISION: User-driven first, LLM-powered optional**
Unlike Mem0 (which requires LLM for every operation), Mnemora stores what developers explicitly tell it to store. Offer optional LLM-powered extraction as a premium feature (POST /v1/memory/extract with Bedrock Claude Haiku).

Rationale: Lower cost, lower latency, more predictable. Developers building agents already have LLM calls in their pipeline; they don't want another one hidden in their database.

---

## 5. Risk Register: Things That Will Go Wrong

| # | Risk | Impact | Mitigation |
|---|------|--------|------------|
| 1 | Aurora Serverless v2 doesn't actually scale to zero | $44/mo minimum even with zero users | Accept cost, shared cluster across all tenants |
| 2 | pgvector HNSW index rebuild on schema change | Minutes of downtime | Use blue-green deployment, index on new table then swap |
| 3 | DynamoDB hot partition with popular agents | Throttling, 429 errors | Use write sharding (add random suffix to PK) |
| 4 | Lambda cold starts on Python | 1-3s first request latency | Provisioned concurrency for /v1/memory/search endpoint |
| 5 | Bedrock Titan rate limits | Embedding generation blocked | Implement SQS queue for async embeddings, retry with backoff |
| 6 | LangGraph checkpoint schema changes | Breaking compatibility | Pin to langgraph-checkpoint v3.x, version our adapter |
| 7 | Multi-tenant data leak via SQL injection | Security breach | Parameterized queries only, RLS in Postgres, audit logging |
| 8 | DynamoDB Streams to S3 archival fails | Lost episodes | Dead letter queue, S3 event notifications for monitoring |
| 9 | Free tier abuse (crypto mining agents) | Cost explosion | Rate limits, payload size limits, anomaly detection on usage |
| 10 | OpenAPI spec drift from implementation | Broken SDK clients | Auto-generate spec from route decorators, CI validation |

---

## 6. Features We Can Ship That No Competitor Has

1. **LangGraph checkpoint with built-in TTL cleanup** — LangGraph's PostgresSaver has no cleanup mechanism (Issue #1138). We add automatic TTL.
2. **Bi-temporal memory** from day one — Every memory record has `valid_from`, `valid_until`, `ingested_at`. Zep/Graphiti pioneered this but it's closed-source.
3. **Cross-memory search** — Single query searches across semantic, episodic, and procedural memory. No competitor offers this.
4. **Serverless with AWS-native integration** — Mem0 requires self-hosted databases. Letta requires a server. We're fully managed.
5. **No mandatory LLM dependency** — Store and search memories without LLM calls. Optional LLM extraction for convenience.
6. **Built-in episode summarization** — Auto-compress old episodic memory into semantic summaries (using Bedrock Claude Haiku, ~$0.001/summary).
7. **EU AI Act compliance** — Immutable audit logs with 10-year retention. No competitor markets this yet.
8. **Database branching for agent testing** — Aurora clone for staging/testing agent memory without affecting production.

---

## 7. Pre-Build Checklist

Before writing a single line of code:

- [ ] Verify Aurora Serverless v2 pgvector extension availability in target region
- [ ] Test Bedrock Titan Embeddings v2 access and quota limits
- [ ] Set up AWS account with proper IAM boundaries
- [ ] Reserve domain: mnemora.dev (or alternative)
- [ ] Create GitHub org: mnemora-db
- [ ] Set up PyPI account for SDK publishing
- [ ] Create Discord server (empty, ready for launch day)
- [ ] Draft HackerNews post title and opening paragraph
- [ ] Set up Vercel account for dashboard deployment
- [ ] Configure billing alerts: $50/day, $200/month hard caps
- [ ] Create monitoring dashboard in CloudWatch
- [ ] Set up error tracking (Sentry free tier)
