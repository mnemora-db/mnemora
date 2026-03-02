# HackerNews — Show HN Post

**Title:** Show HN: Mnemora – Open-source memory infrastructure for AI agents

**Word count:** 279

---

**Post body:**

AI agents are stateless by default. When a session ends, they forget everything — what the user said, what tools they called, what decisions they made. Most developers fix this by stitching together Redis for state, Pinecone for vectors, Postgres for history, and S3 for logs. That's four separate databases, four billing accounts, and four failure surfaces for what should be a solved problem.

Mnemora is a single REST API backed by four storage engines, each matched to a specific memory type:

- **Working memory** — Key-value state in DynamoDB. Optimistic locking via version integers. TTL support. Warm round-trip: ~150ms.
- **Semantic memory** — Text stored as 1024-dimensional vectors via Bedrock Titan Text Embeddings v2, indexed with HNSW (m=16, ef_construction=200) in Aurora Serverless v2 + pgvector. Cosine dedup at >0.95 similarity. Store latency: ~3-4s (Bedrock call + Aurora insert). Cold start: ~7s (VPC + Aurora resume).
- **Episodic memory** — Append-only time-series logs. DynamoDB for hot data, S3 for cold tiering. Time-range queries and session replay.
- **Procedural memory** — Schema deployed (tool definitions, rules in Postgres). SDK methods shipping in v0.2.

The SDK ships with framework integrations already built and tested: `MnemoraCheckpointSaver` for LangGraph (extends `BaseCheckpointSaver`), `MnemoraMemory` for LangChain (extends `BaseChatMessageHistory`), and `MnemoraCrewStorage` for CrewAI. No LLM call is required for CRUD operations — that's a meaningful difference from alternatives that require a model call on every write.

Self-host with AWS CDK: `npx cdk deploy`. Estimated idle cost on AWS: ~$15/month.

446 tests passing (330 API + 116 SDK). MIT license for the SDK.

```python
pip install mnemora
```

GitHub: https://github.com/mnemora-dev/mnemora

Happy to answer questions about the architecture, trade-offs in the storage tier choices, or the LangGraph integration design.
