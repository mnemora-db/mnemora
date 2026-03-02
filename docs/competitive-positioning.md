# Mnemora Competitive Positioning

**Last updated:** 2026-03-02
**Status:** Internal reference — not for external publication without review

This document is for internal use by the Mnemora team. It is intended to inform product decisions, sales conversations, and marketing content. Every Mnemora claim in this document has been verified against the codebase as of the date above. Competitor claims are based on publicly available documentation, GitHub repositories, and published research as of the same date.

---

## How to use this document

Read the weaknesses section for each competitor with the same care you give the strengths. Credibility in technical communities depends on honest self-assessment. Do not use this document to cherry-pick favorable comparisons for marketing copy. Use it to understand where Mnemora has a real edge, where it does not, and what objections to prepare for.

---

## 1. Competitor Deep Dives

### 1.1 Mem0

**What it does.** Mem0 is a memory extraction and storage SDK. It intercepts conversational turns, uses an LLM to decide which facts are worth remembering, and writes those extracted memories to a user-managed vector store. It is not a database — it is a layer that sits in front of databases you provision yourself.

**Architecture.** Every memory operation runs a two-phase LLM pipeline: an extraction phase where a prompt instructs the model to produce candidate memories from the current conversation turn, followed by an update phase where the same or a second LLM call compares candidates against existing memories and issues tool calls to CREATE, UPDATE, DELETE, or NOOP. The default extraction model is gpt-4.1-nano. Storage backends are user-configured: vector store (Qdrant, Pinecone, Chroma, or pgvector), optional graph store (Neo4j or FalkorDB), and optional key-value store (Redis). Version 1.0 added async-by-default operation, rerankers, and Azure OpenAI support. The OpenMemory MCP project extends Mem0's reach toward a portable memory standard.

**Strengths.**
- Automatic memory extraction from conversations. Developers do not need to decide what to store — the LLM decides.
- Large community. Approximately 43K GitHub stars as of early 2026, which means a wide ecosystem of tutorials, examples, and framework-specific guides.
- Breadth of vector store integrations. Works with Qdrant, Pinecone, Weaviate, Chroma, and pgvector, so it fits into existing stacks.
- Confidence scoring with temporal decay. Memories have a score that decreases over time, which is a reasonable heuristic for prioritizing retrieval.
- Graph memory option. Neo4j/FalkorDB support for entity-relationship extraction provides richer retrieval for some use cases.
- OpenMemory MCP signals a community standard forming around the Mem0 API shape.

**Weaknesses.**
- Every memory operation requires an LLM call. At scale, this adds 200–500ms of latency and approximately $0.001–0.01 per operation in LLM cost on top of storage costs. For agents that process thousands of turns per day, this is non-trivial.
- No managed database. Users must provision, maintain, and pay for a vector store, optional graph store, and optional key-value store. The operational burden of three separate databases is the exact problem Mnemora was built to eliminate.
- No checkpoint support. Mem0 has no mechanism for saving LangGraph or other agent framework checkpoint state. This is a fundamental gap for stateful multi-step agents.
- No episodic memory with time-range queries. Mem0 does not offer an append-only event log with session replay. You can retrieve memories, but you cannot replay what an agent did step-by-step through a session.
- No native tiered storage. There is no automatic hot-to-cold archiving of older data.
- No GDPR purge endpoint. Deleting all data for a user requires manual operations across multiple databases.
- No serverless deployment option. If you self-host Mem0 with a Qdrant backend, that infrastructure runs continuously regardless of traffic.

**Pricing model.** Open-source SDK under Apache 2.0 for self-hosted use. Mem0 Cloud (managed) offers a free tier and paid plans; exact pricing changes frequently and should be verified at mem0.ai. The open-source model means zero license cost for self-hosted deployments, but operational costs for the underlying databases are real.

**GitHub stars / community size.** Approximately 43K stars. Active Discord community. Growing adoption through LangChain and CrewAI ecosystem tutorials.

**Key differentiator vs Mnemora.** The core architectural difference is mandatory LLM dependency vs. optional LLM dependency. Mem0 cannot perform a basic write without an LLM call. Mnemora's handlers (`api/handlers/state.py`, `api/handlers/semantic.py`, `api/handlers/episodic.py`) perform CRUD operations entirely through DynamoDB and Aurora — no LLM is involved unless you explicitly call the summarization endpoint (`POST /v1/memory/episodic/{agent_id}/summarize`), which is opt-in. The second difference is infrastructure consolidation: Mnemora is the database, not a wrapper around databases you manage.

---

### 1.2 Zep / Graphiti

**What it does.** Zep originally offered a managed memory service with conversation history and semantic search. The company has pivoted to a closed-source commercial platform. Graphiti — their temporal knowledge graph engine — remains open-source and is the technically interesting part of their portfolio.

**Architecture.** Graphiti's design centers on a bi-temporal model: every fact in the graph has a `valid_at` timestamp (when it became true in the world) and an `invalid_at` timestamp (when it stopped being true). This allows the system to answer questions like "what did the agent believe about the user's location last Tuesday?" without overwriting historical facts. Retrieval combines semantic embedding search, BM25 keyword search, and graph traversal. Reranking uses Reciprocal Rank Fusion (RRF), Maximal Marginal Relevance (MMR), and cross-encoder models. The primary graph backend is Neo4j; FalkorDB and Amazon Neptune are also supported. Graphiti requires an LLM for graph construction (gpt-4o-mini by default) and BGE-m3 for embedding and reranking. The commercial Zep platform is closed-source; only Graphiti's graph engine is available under an open-source license.

**Strengths.**
- Bi-temporal data model. The `valid_at` / `invalid_at` approach is the most principled way to handle facts that change over time. A user's home city, preferences, or job title should be versioned, not overwritten.
- Sub-200ms retrieval latency cited in published benchmarks (arXiv:2501.13956) for the graph traversal + hybrid search combination.
- Outperforms MemGPT on the DMR benchmark (94.8% vs 93.4%), providing published evidence of retrieval quality.
- Incremental real-time updates. New episodes are integrated into the graph without batch recomputation.
- Hybrid retrieval. The combination of semantic, keyword, and graph search covers a wider range of retrieval patterns than vector-only approaches.

**Weaknesses.**
- Neo4j dependency is a heavy infrastructure requirement. Neo4j Community Edition has license restrictions; Neo4j Enterprise is expensive. Teams that want to avoid graph database operations are excluded.
- LLM required for graph construction. Every new episode triggers an LLM call to extract entity-relationship triples. Same cost and latency problem as Mem0 for write-heavy workloads.
- Commercial platform is closed-source. Graphiti is open-source, but Zep's managed service — which includes the UI, multi-tenancy, and production features — is not. You cannot inspect what you are running in production.
- No serverless deployment. Zep requires running a persistent server process.
- No LangGraph checkpoint compatibility. Graphiti provides entity memory but not the `BaseCheckpointSaver` interface that LangGraph agents need to resume across invocations.
- No tiered cold storage for episodic data.

**Pricing model.** Graphiti is open-source (Apache 2.0). Zep Cloud has a free tier and paid plans; pricing is not publicly disclosed on the pricing page as of this writing and requires a sales conversation for larger deployments.

**GitHub stars / community size.** Graphiti repository has grown significantly following the DMR benchmark publication. Zep had ~10K stars before the pivot; Graphiti is growing separately.

**Key differentiator vs Mnemora.** Graphiti's bi-temporal model is genuinely more sophisticated than Mnemora's current `valid_from` / `valid_until` fields on semantic memory. Mnemora has the schema columns defined (see `CLAUDE.md` Aurora schema: `valid_from TIMESTAMPTZ DEFAULT now()`, `valid_until TIMESTAMPTZ`) but the application layer does not yet perform automatic fact invalidation when contradictory information arrives — that logic is not implemented in `api/handlers/semantic.py`. This is an honest gap. Mnemora's advantage over Graphiti is infrastructure simplicity: no Neo4j, no persistent server, serverless deployment via AWS CDK, and first-class LangGraph checkpoint support.

---

### 1.3 Letta / MemGPT

**What it does.** Letta (formerly MemGPT) is an agent framework and server that implements a tiered memory model inspired by operating system memory management. It treats LLM context windows like RAM and external storage like disk. The agent itself decides what to move between tiers using tool calls.

**Architecture.** The foundational MemGPT design divides memory into core memory (small, always in the LLM's context window — a `human` block describing the user and a `persona` block defining the agent's identity) and archival memory (large external storage the agent can search and append to via tool calls). Recall memory provides searchable conversation history. Memory blocks are labeled key-value pairs with configurable character limits. Version 1 of the Letta server introduced context repositories (git-style versioning for memory state), sleep-time compute (agents refine memory asynchronously during idle periods), and skill learning (agents improve behavior from past experience). Letta uses PostgreSQL as its persistence layer, which validates Aurora as a reasonable backend choice. The Letta server is a persistent process that must be deployed and maintained.

**Strengths.**
- Self-editing memory is a compelling UX for certain use cases: the agent maintains its own world model and updates it autonomously.
- Memory blocks concept is simple and effective. Labeled, size-limited chunks that are always in context cover a wide range of use cases with minimal configuration.
- 42K GitHub stars reflects substantial community investment and tutorial coverage.
- Sleep-time compute is an interesting capability for agents that need to consolidate knowledge without user-facing latency impact.
- Model-agnostic: works with any LLM that supports tool calling.
- Validated PostgreSQL backend: Letta's own persistence layer is Postgres, confirming Aurora as a solid foundation.

**Weaknesses.**
- Requires running a full server process. Letta cannot be deployed serverless. This is a significant operational difference from Mnemora's Lambda-based architecture.
- Self-editing memory is risky without guardrails. Agents can corrupt their own memory, and rollback is not trivially available.
- Tightly coupled to the agent loop. Letta is an agent framework, not a memory database. If you are building with LangGraph, CrewAI, or AutoGen, integrating Letta means adopting another framework's opinions about agent architecture.
- No native vector search endpoint. Memory search in Letta is mediated through the agent's own tool calls, not a direct semantic search API you can call from outside.
- Heavy server requirement creates cold-start friction for development: you need a running Letta server before you can test anything.
- No tiered storage: Letta does not implement hot/cold archiving for episodic data.

**Pricing model.** Open-source under Apache 2.0. Letta Cloud (managed) is available; pricing requires contacting the team. Self-hosted deployment requires provisioning a server and PostgreSQL database.

**GitHub stars / community size.** Approximately 42K stars, concentrated among developers who want the agent-self-editing memory paradigm.

**Key differentiator vs Mnemora.** Letta is a framework with memory; Mnemora is a memory database for any framework. A developer using LangGraph should not need to adopt Letta's agent loop to get persistent memory — they should add `MnemoraCheckpointSaver` (see `sdk/mnemora/integrations/langgraph.py`) and gain state persistence without changing their agent's architecture. Mnemora's episodic memory (`api/handlers/episodic.py`) also provides the append-only audit log that Letta's archival memory does not — you can replay exactly what an agent did in a session in chronological order, which is essential for debugging and compliance.

---

### 1.4 DIY Approach: Redis + Pinecone + Postgres (or equivalent)

**What it does.** Many production agent teams do not use a dedicated memory library at all. They wire up Redis for session state, Pinecone (or another managed vector store) for semantic search, and a general-purpose Postgres instance for relational data and logs.

**Architecture.** No single architecture; varies by team. A representative stack: Redis for working memory with TTL-based expiry, Pinecone or Weaviate for vector embeddings, Postgres for relational data, S3 for raw logs. The developer writes glue code to manage these systems: embedding on write, deduplication logic, session isolation, multi-tenancy enforcement, data purge on delete. Each database has its own SDK, its own auth configuration, its own monitoring setup, and its own backup policy.

**Strengths.**
- Full control. No vendor dependency on a memory-specific product.
- Composable. Each component is best-of-breed for its domain.
- Familiar. Most backend engineers have operational experience with Postgres and Redis.
- No per-operation LLM cost for writes.

**Weaknesses.**
- Glue code accumulates. Every team reinvents multi-tenancy, session isolation, deduplication, TTL management, and GDPR purge. This code is not differentiating and is easy to get wrong.
- Three or more separate billing relationships, monitoring pipelines, and authentication systems.
- No cross-store search. A query that should search both conversation history (episodic) and long-term knowledge (semantic) requires two separate API calls and client-side merge logic.
- No automatic embedding on write. The developer must call an embedding API, handle retries, and pass the vector to the insert.
- No optimistic locking for concurrent state updates without implementing it manually.
- No session replay. Postgres can store events, but building a queryable time-range index for session replay is non-trivial.
- No managed tiering. Moving old data from Postgres to S3 requires writing and maintaining an archival job.

**Pricing model.** Depends on the stack. A representative monthly cost for a small production deployment: Redis Cloud ~$5–30, Pinecone Starter ~$70, Postgres on RDS ~$30–100, S3 minimal. Total: $100–200/month before engineering time. The engineering cost of building and maintaining the integration layer is the larger cost.

**Community size.** Not applicable — this is an approach, not a product.

**Key differentiator vs Mnemora.** The DIY approach is always available and does not go away. Mnemora's value proposition against DIY is time-to-value and operational simplicity: a single API key, one SDK, four memory types, automatic embedding, built-in multi-tenancy, GDPR purge (`DELETE /v1/memory/{agent_id}` in `api/handlers/unified.py`), and cross-store search (`POST /v1/memory/search`) — none of which require the developer to write glue code. The honest counter is that Mnemora adds a new vendor dependency and its own operational risk. Teams with strong infrastructure discipline and existing tooling investment may rationally prefer DIY.

---

## 2. Feature Comparison Matrix

The following table compares Mnemora against the three named competitors and the DIY baseline. A checkmark means the capability is verifiably present. A dash means the capability does not exist or is not documented. A note in parentheses indicates partial support or a significant caveat.

Mnemora claims are verified against the codebase at `/Users/isaacgbc/mnemora/`. All handler logic, SDK code, infrastructure definitions, and schema files were reviewed on 2026-03-02.

| Capability | Mnemora | Mem0 | Zep / Graphiti | Letta / MemGPT | DIY |
|---|---|---|---|---|---|
| **Working memory (key-value state)** | Yes — DynamoDB, `api/handlers/state.py` | No direct equivalent | No | Yes — memory blocks | Yes — Redis or Postgres |
| **Semantic memory (vector search)** | Yes — Aurora pgvector, HNSW index | Yes — via external vector store | Yes — Neo4j + embedding | Yes — archival memory | Yes — Pinecone or pgvector |
| **Episodic memory (time-series log)** | Yes — DynamoDB hot + S3 cold, `api/handlers/episodic.py` | No | No | Partial — recall memory (no time-range query) | Manual Postgres + S3 |
| **Procedural memory (versioned schemas/tools)** | Yes — Aurora, schema defined in `CLAUDE.md`; SDK access planned | No | No | No | Manual Postgres |
| **Vector search engine** | pgvector on Aurora Serverless v2, HNSW (m=16, ef_construction=200) | External (Qdrant, Pinecone, Chroma, pgvector) | Neo4j + embedding | Postgres + pgvector | External (Pinecone, Weaviate, pgvector) |
| **LLM required for CRUD** | No — embeddings auto-generated server-side; no LLM for state/episodic writes | Yes — every add/update triggers LLM extraction | Yes — LLM for graph construction | Yes — agent uses tool calls to manage memory | No |
| **Deployment model** | Serverless — AWS Lambda + HTTP API Gateway | Self-hosted (managed vector DB required) or Mem0 Cloud | Self-hosted (Neo4j required) or Zep Cloud (closed-source) | Self-hosted persistent server or Letta Cloud | Self-hosted |
| **Self-hostable** | Yes — AWS CDK in `infra/` | Yes | Graphiti yes; Zep platform no | Yes | Yes — it is DIY |
| **Multi-tenancy** | Yes — Lambda authorizer derives `tenant_id` from API key; DynamoDB PK prefix + Aurora RLS | Partial — SDK-level user/agent scoping | Partial — Zep Cloud only; Graphiti has no tenant model | No native multi-tenancy | Manual |
| **LangGraph checkpoint** | Yes — `MnemoraCheckpointSaver` in `sdk/mnemora/integrations/langgraph.py`; `aget`, `aput`, `aput_writes`, `alist` implemented | No | No | No | Manual implementation against `BaseCheckpointSaver` |
| **LangChain integration** | Yes — `MnemoraMemory` in `sdk/mnemora/integrations/langchain.py`; `BaseChatMessageHistory` implemented | Yes — first-party | No official package | No | Manual |
| **CrewAI integration** | Yes — `MnemoraCrewStorage` in `sdk/mnemora/integrations/crewai.py`; `Storage` interface implemented | Yes — community adapters | No | No | Manual |
| **Optimistic locking** | Yes — `version` integer on state items; `ConditionalCheckFailedException` handling in `api/handlers/state.py` | No | No | No | Manual (application-level) |
| **Tiered cold storage** | Yes — DynamoDB (hot, 48-hour TTL) → S3 (cold); S3 lifecycle to Glacier at 90 days; defined in `infra/lib/mnemora-stack.ts` | No | No | No | Manual archival job |
| **GDPR data purge** | Yes — `DELETE /v1/memory/{agent_id}` purges DynamoDB + Aurora + S3; implemented in `api/handlers/unified.py` | No single-call purge | No | No | Manual across systems |
| **Cross-store search** | Yes — `POST /v1/memory/search` merges semantic (vector) + episodic (text match); `api/handlers/unified.py` | No — semantic only | No | No | Manual + client-side merge |
| **Session replay** | Yes — `GET /v1/memory/episodic/{agent_id}/sessions/{session_id}`; chronological episode list | No | No | No | Manual |
| **Deduplication on write** | Yes — cosine similarity > 0.95 check before insert; `api/handlers/semantic.py` | Yes — similar mechanism | Partial — graph update logic | No | Manual |
| **Automatic embedding** | Yes — Bedrock Titan Text Embeddings v2, 1024 dims, triggered server-side on `POST /v1/memory/semantic` | Yes — requires LLM + embedding provider | Yes — BGE-m3 | Yes — via Postgres pgvector | Manual |
| **Embedding model** | Amazon Bedrock Titan v2 (`amazon.titan-embed-text-v2:0`), 1024 dims | Configurable (OpenAI, Cohere, etc.) | BGE-m3 | OpenAI or configurable | Configurable |
| **Content chunking** | Yes — overlapping chunks for content > ~8K tokens; `api/lib/embeddings.py`, `generate_embeddings_chunked` | Yes — automatic | Partial | No | Manual |
| **TTL-based expiry** | Yes — DynamoDB native TTL on all items; configurable per-request via `ttl_hours` | No | No | No | Manual (Redis TTL or cron job) |
| **Checkpoint TTL cleanup** | Yes — `ttl TIMESTAMPTZ` column added to checkpoints table in Aurora schema | No — LangGraph issue #1138 (known gap) | No | No | Manual |
| **Namespace support** | Yes — semantic memory has `namespace` column; search filterable by namespace | No | No | No | Manual |
| **Metadata filtering** | Yes — JSONB containment filter on semantic search (`metadata @> %s::jsonb`); `api/handlers/semantic.py` | Yes — metadata filtering | Partial | No | Manual |
| **Bi-temporal model** | Partial — `valid_from` and `valid_until` columns exist in Aurora schema; automatic fact invalidation on contradiction is not yet implemented | No | Yes — full bi-temporal model is Graphiti's core feature | No | Manual |
| **Observability** | Yes — CloudWatch dashboards, Lambda error rate alarms, Aurora ACU alarms, DynamoDB throttle alarms; `infra/lib/mnemora-stack.ts` | No built-in | No | No | Manual |
| **Pricing** | Free ($0/1K calls/day), Starter ($19/mo), Pro ($79/mo), Scale ($299/mo); see `docs/site/pricing.md` | Free (self-hosted) + Mem0 Cloud plans | Free (Graphiti, self-hosted) + Zep Cloud (pricing not public) | Free (self-hosted) + Letta Cloud | Depends on stack; typically $100–200/month managed + engineering |

---

## 3. Positioning Statement

**Against Mem0:** Mnemora is the right choice when you need memory storage that does not depend on an LLM call at write time. Mem0 is a memory extraction system — it decides what to remember by asking an LLM. Mnemora is a memory database — it stores what you tell it to store. For agents where you control the data model, where write latency and cost matter at scale, and where you need a single API for state, vector search, and event logs rather than three separate databases, Mnemora is the more appropriate foundation.

**Against Zep / Graphiti:** Zep's commercial platform is closed-source. Graphiti's bi-temporal graph model is architecturally sophisticated but requires Neo4j and LLM calls for every write. Mnemora trades some of Graphiti's retrieval depth for operational simplicity: no graph database, no persistent server, and a serverless deployment that scales to zero between agent runs. For teams on AWS who need LangGraph checkpoint support and a managed service they can inspect and self-host, Mnemora is the more practical choice. Teams who need automatic fact invalidation across a temporal knowledge graph and are willing to run Neo4j should evaluate Graphiti seriously.

**Against Letta / MemGPT:** Letta is a framework that contains memory. Mnemora is memory that integrates with any framework. If you are already using LangGraph, CrewAI, or a custom agent architecture, you do not need to adopt Letta's agent loop to get persistent memory. You add `MnemoraCheckpointSaver` or `MnemoraMemory` and keep your existing architecture. Mnemora also provides the append-only episodic log and session replay that Letta does not, which is important for debugging multi-step agents and satisfying audit requirements.

**Against DIY:** The DIY stack gives you maximum control and avoids new vendor risk. Mnemora is the right choice when the cost of building and maintaining multi-tenancy, deduplication, GDPR purge, cross-store search, and automatic tiering exceeds the cost of a vendor dependency. That crossover typically happens when you are past the prototype stage and the glue code is consuming engineering time that should be on product work.

---

## 4. Target Developer Personas

### 4.1 The LangGraph user who needs state persistence

**Profile:** Building a multi-step research agent or workflow orchestrator with LangGraph. The agent breaks down tasks, uses tools, and needs to resume across Lambda cold starts or multiple user sessions.

**Current situation:** Using `langgraph-checkpoint-postgres` directly, self-managing a Postgres instance, and discovering there is no built-in TTL for checkpoint cleanup (LangGraph issue #1138).

**Why Mnemora:** `MnemoraCheckpointSaver` plugs directly into LangGraph's `compile(checkpointer=saver)` interface. The checkpoint schema in Aurora includes a `ttl` column that does not exist in the standard `langgraph-checkpoint-postgres` implementation. State persistence, semantic memory for retrieved context, and episodic logs for the agent's action history are all on the same API key with no additional infrastructure.

**Objection to address:** "I already have Postgres." The Mnemora checkpoint table is compatible with `langgraph-checkpoint-postgres`'s schema — same primary keys and columns — with the addition of the `ttl` column. The integration is a one-line change to `checkpointer=`. The managed Aurora Serverless v2 instance eliminates the operational overhead of a self-managed Postgres, at the cost of a vendor dependency.

### 4.2 The AWS-native team that refuses new infrastructure

**Profile:** Full-stack engineer or small team that has standardized on AWS. Uses DynamoDB for application state, already has a VPC, and does not want to introduce Pinecone, Qdrant, or any non-AWS managed service.

**Current situation:** Manually implementing vector search either through a pgvector instance they manage or through an external service that complicates their IAM and VPC setup.

**Why Mnemora:** Everything runs in the customer's own AWS account or on Mnemora's AWS-native infrastructure. The CDK stack in `infra/` is a complete, self-hostable deployment. Aurora Serverless v2 for pgvector, DynamoDB on-demand, S3 with lifecycle rules — all AWS-native, all visible in CloudWatch, all manageable with existing AWS IAM policies.

**Objection to address:** "We already pay for DynamoDB and don't want another RDS cost." Aurora Serverless v2 has a minimum ACU of 0.5 (approximately $44/month on the managed service). Mnemora Cloud amortizes this across tenants on the lower tiers so individual accounts do not bear the floor cost. The self-hosted CDK option means the team controls the cost directly.

### 4.3 The CrewAI multi-agent pipeline builder

**Profile:** Building a research or content pipeline with multiple specialized CrewAI agents. Needs agents to share context across runs, store extracted knowledge for reuse, and not re-derive the same facts on every execution.

**Current situation:** Using in-memory CrewAI storage (lost between runs) or implementing a custom Redis-based storage backend.

**Why Mnemora:** `MnemoraCrewStorage` implements CrewAI's `Storage` interface directly. Agents store plans and results as working memory keyed by session. Semantic memory accumulates extracted knowledge across runs and is retrievable by similarity query. `POST /v1/memory/search` provides cross-store search without the developer implementing merge logic.

**Objection to address:** "Mem0 has a CrewAI integration too." Mem0's CrewAI integration writes extracted memories to an LLM-filtered semantic store. Mnemora stores what the agents explicitly write and provides the same retrieval — without requiring an LLM call per write. For pipelines that run frequently with structured outputs, the cost and latency difference compounds quickly.

### 4.4 The developer building a production chatbot with compliance requirements

**Profile:** Building a customer-facing assistant that stores conversation history. Needs GDPR-compliant data deletion, audit logs of what the agent did, and the ability to demonstrate data isolation between customers.

**Current situation:** Rolling their own Postgres schema for conversation history, manually writing delete cascades for user data deletion, and lacking a clean audit trail of agent actions.

**Why Mnemora:** `DELETE /v1/memory/{agent_id}` purges all data across DynamoDB, Aurora, and S3 in a single call — verified in `api/handlers/unified.py`. The episodic memory log provides an immutable append-only record of every action, observation, and conversation turn. Multi-tenancy is enforced at the Lambda authorizer layer — client-provided `tenant_id` is never trusted. Each API key maps to exactly one tenant with no cross-contamination possible.

**Objection to address:** "Can we audit what Mnemora stores?" Yes. The episodic memory API (`GET /v1/memory/episodic/{agent_id}/sessions/{session_id}`) returns the full chronological record of every episode stored for a session. The Aurora schema stores all semantic memories with `created_at`, `updated_at`, and `valid_until` timestamps.

---

## 5. Objection Handling

**"Aurora Serverless v2 doesn't scale to zero. There's a $44/month minimum."**

This is accurate. Aurora Serverless v2 has a minimum capacity of 0.5 ACU, which costs approximately $0.12/ACU-hour and produces a floor of roughly $44/month. This is documented honestly in `docs/architecture/open-source-analysis.md` under section 3.1. On the Mnemora managed service, the shared multi-tenant cluster amortizes this cost across all tenants on lower-tier plans. On the self-hosted CDK deployment, the team bears this cost directly. If the Aurora floor is prohibitive for your scale, evaluate whether Neon Serverless Postgres (true scale-to-zero with pgvector support) would reduce the infrastructure cost at the expense of leaving the AWS ecosystem.

**"Mem0 has 43K GitHub stars. Mnemora has almost none."**

Community size and correctness of architecture are different things. Mem0's star count reflects early leadership in a category that is still being defined. Mnemora's architecture makes a different tradeoff: no mandatory LLM calls, unified database rather than a wrapper, and LangGraph checkpoint compatibility. For production use, the relevant question is whether the architecture fits the use case — not whether the project has the most stars.

**"Why not just use Pinecone for vectors and Redis for state? I know how those work."**

That is a completely rational choice for many teams. Mnemora's value proposition against the DIY stack is that the glue code — multi-tenancy enforcement, deduplication, GDPR purge, cross-store search, session replay, automatic tiering — is already written and maintained. If your team has the infrastructure discipline to build and own that layer reliably, DIY is fine. If that layer is absorbing engineering time that should be on product work, Mnemora is worth evaluating.

**"Graphiti's temporal knowledge graph retrieval is more sophisticated than pgvector cosine similarity."**

Correct. Graphiti's bi-temporal model with entity-relationship extraction, BM25 hybrid search, and graph-based reranking produces better retrieval for complex, long-running agents that need to reason about fact history. Mnemora's `valid_from` / `valid_until` columns exist in the schema but automatic fact invalidation on contradiction is not yet implemented. If you need the full bi-temporal graph model and are willing to run Neo4j, Graphiti is worth serious evaluation. Mnemora's advantage in that comparison is operational simplicity and LangGraph checkpoint support, not retrieval depth.

**"What happens to my data if Mnemora shuts down?"**

Mnemora is self-hostable via the CDK stack in `infra/`. If the managed service is discontinued, you can deploy the same stack to your own AWS account. The data is in standard AWS services — DynamoDB, Aurora PostgreSQL, and S3 — with no proprietary encoding. Export from DynamoDB is standard; Aurora PostgreSQL exports via `pg_dump`. There is no lock-in to a custom storage format.

**"Letta has self-editing memory. My agent can update its own beliefs."**

Letta's self-editing memory block is a useful pattern for agents that should maintain an autonomous world model. Mnemora does not implement agent-initiated self-editing. Mnemora's working memory API (`PUT /v1/state/{agent_id}`) uses optimistic locking — the agent can update its state if it holds the correct version, which prevents lost updates in concurrent scenarios but does not implement the MemGPT-style persona/human block architecture. If the self-editing paradigm is central to your agent's design, Letta is the more natural fit.

**"Procedural memory is not accessible via the SDK."**

Correct. Procedural memory — tool definitions, schemas, prompts, and rules stored in `procedural_memory` in Aurora — is accessible via the database schema directly in this version. SDK methods for procedural memory are planned but not yet implemented. If you need programmatic CRUD on tool definitions via the SDK today, this is a real gap. The schema is defined and the Aurora table exists; the API handlers and SDK methods are on the roadmap.

---

## Appendix: Verified Codebase Claims

The following Mnemora capabilities were directly verified against source files before writing this document.

| Claim | Source |
|---|---|
| Working memory CRUD with optimistic locking | `/Users/isaacgbc/mnemora/api/handlers/state.py` — `_handle_update` uses `ConditionalCheckFailedException` handling |
| Semantic memory with pgvector + cosine similarity | `/Users/isaacgbc/mnemora/api/handlers/semantic.py` — `1 - (embedding <=> %s::vector) > 0.95` deduplication query |
| Deduplication on semantic writes | `/Users/isaacgbc/mnemora/api/handlers/semantic.py` — lines 347–405, cosine similarity check before INSERT |
| Episodic memory with time-range queries | `/Users/isaacgbc/mnemora/api/handlers/episodic.py` — `_handle_query` accepts `from_time`, `to_time` query params |
| Session replay endpoint | `/Users/isaacgbc/mnemora/api/handlers/episodic.py` — `_handle_session_replay` returns chronological episode list |
| GDPR purge across all stores | `/Users/isaacgbc/mnemora/api/handlers/unified.py` — `_handle_purge` deletes from DynamoDB + Aurora + S3 |
| Cross-store search (semantic + episodic) | `/Users/isaacgbc/mnemora/api/handlers/unified.py` — `_handle_search` merges pgvector results with episodic text-match |
| Auto-embedding via Bedrock Titan v2 | `/Users/isaacgbc/mnemora/api/lib/embeddings.py` — `generate_embedding` calls `amazon.titan-embed-text-v2:0` |
| Content chunking for large payloads | `/Users/isaacgbc/mnemora/api/lib/embeddings.py` — `generate_embeddings_chunked`, overlapping 512-token chunks |
| LangGraph CheckpointSaver | `/Users/isaacgbc/mnemora/sdk/mnemora/integrations/langgraph.py` — `MnemoraCheckpointSaver` implements `aget`, `aput`, `aput_writes`, `alist` |
| LangChain BaseChatMessageHistory | `/Users/isaacgbc/mnemora/sdk/mnemora/integrations/langchain.py` — `MnemoraMemory` implements `add_message`, `messages`, `clear` |
| CrewAI Storage interface | `/Users/isaacgbc/mnemora/sdk/mnemora/integrations/crewai.py` — `MnemoraCrewStorage` implements `save`, `load`, `delete`, `list_keys`, `search` |
| DynamoDB single-table design | `/Users/isaacgbc/mnemora/infra/lib/mnemora-stack.ts` — lines 86–103, PAY_PER_REQUEST, TTL attribute, GSI |
| Aurora Serverless v2 (PostgreSQL 15.8) | `/Users/isaacgbc/mnemora/infra/lib/mnemora-stack.ts` — lines 117–141, min 0.5 ACU, max 4 ACU |
| S3 lifecycle tiering to Glacier | `/Users/isaacgbc/mnemora/infra/lib/mnemora-stack.ts` — lines 154–170, IA at 30 days, Glacier at 90 days |
| HNSW index on embeddings | `CLAUDE.md` Aurora schema section — `USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200)` |
| Multi-tenancy via Lambda authorizer | `CLAUDE.md` multi-tenancy section + `api/handlers/state.py` line 51–56, tenant_id derived from authorizer context |
| API deployed and live | `/Users/isaacgbc/mnemora/docs/deployment-outputs.md` — stack deployed 2026-03-02, API endpoint active |
| Checkpoint TTL column (not in standard LangGraph schema) | `CLAUDE.md` Aurora schema — `ttl TIMESTAMPTZ` in checkpoints table |
| Procedural memory schema defined, SDK access not yet implemented | `CLAUDE.md` Aurora schema + `docs/site/concepts.md` — "SDK support is planned for a future release" |
| Bi-temporal columns exist, automatic invalidation not implemented | `CLAUDE.md` Aurora schema — `valid_from`, `valid_until` columns defined; no invalidation logic in `api/handlers/semantic.py` |
