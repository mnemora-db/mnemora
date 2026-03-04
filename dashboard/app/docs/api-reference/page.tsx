import { MarkdownRenderer } from "@/components/docs/markdown-renderer";

const content = `# API Reference

Base URL: \`https://0l1lfs30sk.execute-api.us-east-1.amazonaws.com\`

All endpoints are prefixed with \`/v1/\`.

## Authentication

Pass your API key as a Bearer token on every request.

\`\`\`bash
Authorization: Bearer mnm_your_api_key_here
\`\`\`

\`GET /v1/health\` does not require authentication.

## Response envelope

**Success:**

\`\`\`json
{
  "data": { ... },
  "meta": {
    "request_id": "req_01j...",
    "latency_ms": 14
  }
}
\`\`\`

**Error:**

\`\`\`json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "No state found for agent agent-1"
  },
  "meta": {
    "request_id": "req_01j...",
    "latency_ms": 8
  }
}
\`\`\`

---

## Health

### GET /v1/health

Check API availability. No authentication required.

\`\`\`bash
curl https://0l1lfs30sk.execute-api.us-east-1.amazonaws.com/v1/health
\`\`\`

**Response \`200\`:**

\`\`\`json
{ "data": { "status": "ok" }, "meta": { "request_id": "...", "latency_ms": 2 } }
\`\`\`

---

## Working memory

Working memory is backed by DynamoDB. All operations are sub-10ms.

### POST /v1/state

Store or overwrite agent state for a session.

\`\`\`bash
curl -X POST https://0l1lfs30sk.execute-api.us-east-1.amazonaws.com/v1/state \\
  -H "Authorization: Bearer mnm_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "agent-1",
    "session_id": "sess-001",
    "data": { "task": "summarize report", "step": 1 },
    "ttl_hours": 24
  }'
\`\`\`

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| \`agent_id\` | string | Yes | Agent identifier |
| \`data\` | object | Yes | Arbitrary JSON key-value payload |
| \`session_id\` | string | No | Session label. Defaults to \`"default"\` |
| \`ttl_hours\` | integer | No | Hours until automatic expiry. Omit for no expiry |

**Response \`201\`:** Returns a \`StateResponse\` with \`version: 1\`.

---

### GET /v1/state/{agent_id}

Retrieve current state for an agent.

\`\`\`bash
curl https://0l1lfs30sk.execute-api.us-east-1.amazonaws.com/v1/state/agent-1 \\
  -H "Authorization: Bearer mnm_..."
\`\`\`

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| \`session_id\` | string | Filter to a specific session. Defaults to \`"default"\` |

**Response \`200\`:**

\`\`\`json
{
  "data": {
    "agent_id": "agent-1",
    "session_id": "sess-001",
    "data": { "task": "summarize report", "step": 1 },
    "version": 1,
    "created_at": "2026-03-02T10:00:00Z",
    "updated_at": "2026-03-02T10:00:00Z",
    "expires_at": "2026-03-03T10:00:00Z"
  },
  "meta": { "request_id": "...", "latency_ms": 7 }
}
\`\`\`

---

### GET /v1/state/{agent_id}/sessions

List all session IDs for an agent.

---

### PUT /v1/state/{agent_id}

Update state with optimistic locking. Pass the \`version\` from a prior GET or POST. The server rejects the update with \`409\` if the record was modified concurrently.

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| \`data\` | object | Yes | New state payload (replaces existing) |
| \`version\` | integer | Yes | Expected current version |
| \`session_id\` | string | No | Target session. Defaults to \`"default"\` |
| \`ttl_hours\` | integer | No | New TTL |

**Response \`200\`:** Returns \`StateResponse\` with incremented \`version\`.
**Error \`409\`:** Version mismatch — re-read and retry.

---

### DELETE /v1/state/{agent_id}/{session_id}

Delete a specific session's state record.

**Response \`204\`:** No content.
**Error \`404\`:** Session not found.

---

## Semantic memory

Semantic memory is backed by Aurora Serverless v2 with pgvector. Content is automatically embedded via Bedrock Titan.

### POST /v1/memory/semantic

Store text content as a semantic memory entry. The server generates and stores the embedding automatically. Duplicate content (cosine similarity > 0.95) is merged rather than re-inserted.

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| \`agent_id\` | string | Yes | Agent identifier |
| \`content\` | string | Yes | Text to embed and store |
| \`namespace\` | string | No | Logical partition. Defaults to \`"default"\` |
| \`metadata\` | object | No | Arbitrary metadata to attach |

---

### POST /v1/memory/semantic/search

Search semantic memory by natural-language query.

**Body parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| \`query\` | string | Yes | — | Natural-language search string |
| \`agent_id\` | string | No | — | Restrict to one agent |
| \`namespace\` | string | No | — | Restrict to a namespace |
| \`top_k\` | integer | No | 10 | Maximum results |
| \`threshold\` | float | No | 0.7 | Minimum cosine similarity (0–1) |
| \`metadata_filter\` | object | No | — | Exact-match filter on metadata fields |

---

### GET /v1/memory/semantic/{id}

Retrieve a semantic memory record by UUID.

**Error \`404\`:** Record not found or soft-deleted.

---

### DELETE /v1/memory/semantic/{id}

Soft-delete a semantic memory record. Sets \`valid_until\` to now.

**Response \`204\`:** No content.

---

## Episodic memory

Episodic memory is backed by DynamoDB (hot tier) and S3 (cold tier). Records are immutable after creation.

**Episode types:** \`conversation\`, \`action\`, \`observation\`, \`tool_call\`

### POST /v1/memory/episodic

Append a time-stamped episode.

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| \`agent_id\` | string | Yes | Agent identifier |
| \`session_id\` | string | Yes | Session identifier |
| \`type\` | string | Yes | One of: \`conversation\`, \`action\`, \`observation\`, \`tool_call\` |
| \`content\` | any | Yes | Episode payload — text or JSON object |
| \`metadata\` | object | No | Arbitrary metadata |

---

### GET /v1/memory/episodic/{agent_id}

Query episodes with optional time-range and type filters.

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| \`session_id\` | string | Filter to a specific session |
| \`type\` | string | Filter to an event type |
| \`from\` | ISO 8601 | Lower bound timestamp (inclusive) |
| \`to\` | ISO 8601 | Upper bound timestamp (inclusive) |
| \`limit\` | integer | Maximum episodes to return |

---

### GET /v1/memory/episodic/{agent_id}/sessions/{session_id}

Replay all episodes for a session in chronological order.

---

### POST /v1/memory/episodic/{agent_id}/summarize

Compress episodic memory into semantic memories.

---

## Unified

### POST /v1/memory

Auto-route a memory store request by payload shape.

### GET /v1/memory/{agent_id}

Retrieve all memory types for an agent in one call.

### POST /v1/memory/search

Search across semantic and episodic memory simultaneously.

### DELETE /v1/memory/{agent_id}

Permanently delete all data for an agent. Irreversible.

---

## Usage

### GET /v1/usage

Retrieve current billing-period metrics.

---

## Error codes

| HTTP status | Code | Meaning |
|-------------|------|---------|
| 400 | \`VALIDATION_ERROR\` | Request body failed validation |
| 401 | \`UNAUTHORIZED\` | API key is missing, malformed, or revoked |
| 403 | \`FORBIDDEN\` | API key does not have access to the resource |
| 404 | \`NOT_FOUND\` | Resource does not exist |
| 409 | \`CONFLICT\` | Version mismatch on PUT /v1/state |
| 413 | \`PAYLOAD_TOO_LARGE\` | Request body exceeds limit |
| 429 | \`RATE_LIMITED\` | Rate limit exceeded. SDK retries automatically |
| 500 | \`INTERNAL_ERROR\` | Server-side error. Retrying is safe |

---

## Rate limits

| Plan | Requests per day |
|------|-----------------|
| Free | 1,000 |
| Starter | 10,000 |
| Pro | 100,000 |
| Scale | 1,000,000 |
`;

export default function ApiReferencePage() {
  return <MarkdownRenderer content={content} />;
}
