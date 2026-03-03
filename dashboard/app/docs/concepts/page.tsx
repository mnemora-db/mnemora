import { MarkdownRenderer } from "@/components/docs/markdown-renderer";

const content = `# Core Concepts

## Four memory types

Mnemora provides one API for four distinct memory types. Each type maps to a different storage backend and query pattern.

| Memory type | Backend | Analogy | Use when |
|-------------|---------|---------|----------|
| Working | DynamoDB | RAM — current task state | You need fast key-value reads/writes per session |
| Semantic | Aurora + pgvector | Long-term memory — "what I know" | You need to find relevant facts by similarity |
| Episodic | DynamoDB + S3 | Journal — "what happened" | You need a time-ordered log of events |
| Procedural | Aurora (relational) | Skills — "how to do things" | You need versioned tool definitions and schemas |

---

### Working memory

Working memory stores arbitrary JSON state per agent and session. It is backed by DynamoDB and returns in under 10ms.

**Characteristics:**
- Key-value pairs, up to the DynamoDB item size limit
- Optional TTL (hours) for automatic expiry
- Optimistic locking via a \`version\` integer — prevents lost updates when two processes write simultaneously
- Scoped to \`agent_id\` + \`session_id\`

**When to use it:**
- Tracking the current plan or task for an ongoing agent run
- Storing tool call results that need to persist across Lambda invocations
- Holding short-lived context that expires after a session ends

**When NOT to use it:**
- Storing data you need to search by content — use semantic memory instead
- Storing more than a few KB of unstructured text — use episodic memory

---

### Semantic memory

Semantic memory stores text content alongside a 1024-dimensional vector embedding. Search returns the most similar records by cosine similarity.

**Characteristics:**
- Content is automatically embedded via Bedrock Titan Text Embeddings v2 on write
- Deduplication: content with cosine similarity > 0.95 to an existing record is merged, not re-inserted
- Supports namespaces to logically partition memories within an agent
- Soft-delete sets \`valid_until\` — records are excluded from search but not immediately removed
- Search is scoped to a single agent or tenant-wide

**When to use it:**
- Storing facts, preferences, or domain knowledge the agent should recall
- Retrieving relevant context before constructing an LLM prompt
- Building a knowledge base that grows over time

**Embedding details:**
- Model: \`amazon.titan-embed-text-v2:0\`
- Dimensions: 1024
- Similarity metric: cosine similarity (range 0–1, higher is more similar)
- Default search threshold: 0.7 (configurable per query)

---

### Episodic memory

Episodic memory is an append-only, time-ordered log of events. Recent episodes are stored in DynamoDB (hot tier) and automatically tiered to S3 (cold tier) as they age.

**Characteristics:**
- Immutable append — episodes are never updated after creation
- Queryable by time range (\`from_ts\`, \`to_ts\`), event type, and session
- Full session replay via a single API call
- Hot-to-cold tiering is transparent — you query the same endpoint regardless of tier

**Episode types:**

| Type | When to use |
|------|-------------|
| \`conversation\` | Chat messages between user and agent |
| \`action\` | Tool calls, API requests, function executions |
| \`observation\` | Results returned from tools or environment |
| \`tool_call\` | Detailed tool invocation records |

**When to use it:**
- Auditing what an agent did during a session
- Replaying a session to resume or debug
- Feeding a summarization pipeline — \`POST /v1/memory/episodic/{agent_id}/summarize\` converts episodes into semantic memories

---

### Procedural memory

Procedural memory stores versioned tool definitions, JSON schemas, prompts, and rules. It is backed by Aurora PostgreSQL.

**Types:** \`tool\`, \`schema\`, \`prompt\`, \`rule\`

Procedural memory is managed via the Aurora schema directly in this version. SDK support is planned for a future release.

---

## Session model

Every piece of working and episodic memory is scoped to an \`agent_id\` and a \`session_id\`.

- \`agent_id\` — identifies the agent (a logical actor in your system). Reuse the same \`agent_id\` across sessions to accumulate history.
- \`session_id\` — identifies a discrete conversation or task run. Use a new \`session_id\` for each invocation if you want isolated episodes.

Semantic memory is scoped by \`agent_id\` and optionally by \`namespace\`. Sessions do not apply to semantic memory.

**Example:**

\`\`\`
agent_id = "research-agent"
  session_id = "sess-2026-01-15"   ← one research task
  session_id = "sess-2026-01-22"   ← next research task

Semantic namespace = "facts"       ← accumulated knowledge across all sessions
Semantic namespace = "preferences" ← user preferences
\`\`\`

---

## Multi-tenancy model

Every API key maps to exactly one tenant. Mnemora derives your \`tenant_id\` from your API key at the Lambda authorizer layer — you never pass a \`tenant_id\` in requests.

**Isolation guarantees:**

| Layer | Mechanism |
|-------|-----------|
| DynamoDB | Partition key includes \`tenant_id\` prefix |
| Aurora | \`tenant_id\` column + Row-Level Security |
| S3 | Object prefix \`s3://mnemora-data/<tenant_id>/\` |

No request can read or write another tenant's data. All isolation is logical, not physical — the infrastructure is shared.

---

## Vector search

When you call \`store_memory\`, the API sends your content to Bedrock Titan and receives a 1024-dimensional float array. That vector is stored in Aurora alongside the raw text.

When you call \`search_memory\`, the API:
1. Embeds your query with the same Bedrock Titan model
2. Runs an HNSW approximate nearest-neighbor search against all stored vectors for the target agent
3. Filters out results below the similarity threshold
4. Returns up to \`top_k\` results, sorted by similarity (highest first)

**Tuning search:**

| Parameter | Default | Effect |
|-----------|---------|--------|
| \`top_k\` | 10 | Maximum results returned |
| \`threshold\` | 0.7 | Minimum cosine similarity for inclusion |
| \`namespace\` | (all) | Restrict search to a specific namespace |
| \`metadata_filter\` | (none) | Exact-match filter on metadata fields |

Lower \`threshold\` returns more results at lower relevance. Higher \`threshold\` returns fewer, more precise results.
`;

export default function ConceptsPage() {
  return <MarkdownRenderer content={content} />;
}
