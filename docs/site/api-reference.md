# API Reference

Base URL: `https://your-api-id.execute-api.us-east-1.amazonaws.com`

All endpoints are prefixed with `/v1/`. The full OpenAPI specification is at [`docs/openapi.yaml`](../openapi.yaml).

## Authentication

Pass your API key as a Bearer token on every request.

```bash
Authorization: Bearer mnm_your_api_key_here
```

`GET /v1/health` does not require authentication.

## Response envelope

**Success:**

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_01j...",
    "latency_ms": 14
  }
}
```

**Error:**

```json
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
```

---

## Health

### GET /v1/health

Check API availability. No authentication required.

```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/health
```

**Response `200`:**

```json
{ "data": { "status": "ok" }, "meta": { "request_id": "...", "latency_ms": 2 } }
```

---

## Working memory

Working memory is backed by DynamoDB. All operations are sub-10ms.

### POST /v1/state

Store or overwrite agent state for a session.

```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/state \
  -H "Authorization: Bearer mnm_..." \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-1",
    "session_id": "sess-001",
    "data": { "task": "summarize report", "step": 1 },
    "ttl_hours": 24
  }'
```

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | Yes | Agent identifier |
| `data` | object | Yes | Arbitrary JSON key-value payload |
| `session_id` | string | No | Session label. Defaults to `"default"` |
| `ttl_hours` | integer | No | Hours until automatic expiry. Omit for no expiry |

**Response `201`:** Returns a `StateResponse` with `version: 1`.

---

### GET /v1/state/{agent_id}

Retrieve current state for an agent.

```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/state/agent-1 \
  -H "Authorization: Bearer mnm_..."
```

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Filter to a specific session. Defaults to `"default"` |

**Response `200`:**

```json
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
```

**Error `404`:** No state exists for the given agent.

---

### GET /v1/state/{agent_id}/sessions

List all session IDs for an agent.

```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/state/agent-1/sessions \
  -H "Authorization: Bearer mnm_..."
```

**Response `200`:**

```json
{ "data": { "sessions": ["default", "sess-001", "sess-002"] }, "meta": { ... } }
```

---

### PUT /v1/state/{agent_id}

Update state with optimistic locking. Pass the `version` from a prior `GET` or `POST`. The server rejects the update with `409` if the record was modified concurrently.

```bash
curl -X PUT https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/state/agent-1 \
  -H "Authorization: Bearer mnm_..." \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "sess-001",
    "data": { "task": "summarize report", "step": 2 },
    "version": 1
  }'
```

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data` | object | Yes | New state payload (replaces existing) |
| `version` | integer | Yes | Expected current version |
| `session_id` | string | No | Target session. Defaults to `"default"` |
| `ttl_hours` | integer | No | New TTL |

**Response `200`:** Returns `StateResponse` with incremented `version`.
**Error `409`:** Version mismatch — re-read and retry.

---

### DELETE /v1/state/{agent_id}/{session_id}

Delete a specific session's state record.

```bash
curl -X DELETE \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/state/agent-1/sess-001 \
  -H "Authorization: Bearer mnm_..."
```

**Response `204`:** No content.
**Error `404`:** Session not found.

---

## Semantic memory

Semantic memory is backed by Aurora Serverless v2 with pgvector. Content is automatically embedded via Bedrock Titan.

### POST /v1/memory/semantic

Store text content as a semantic memory entry. The server generates and stores the embedding automatically. Duplicate content (cosine similarity > 0.95 with an existing record for the same agent) is merged rather than re-inserted.

```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/semantic \
  -H "Authorization: Bearer mnm_..." \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-1",
    "content": "The user prefers concise bullet-point replies.",
    "namespace": "preferences",
    "metadata": { "source": "conversation", "confidence": 0.9 }
  }'
```

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | Yes | Agent identifier |
| `content` | string | Yes | Text to embed and store |
| `namespace` | string | No | Logical partition within the agent. Defaults to `"default"` |
| `metadata` | object | No | Arbitrary metadata to attach |

**Response `201`:**

```json
{
  "data": {
    "id": "a1b2c3d4-...",
    "agent_id": "agent-1",
    "content": "The user prefers concise bullet-point replies.",
    "namespace": "preferences",
    "metadata": { "source": "conversation", "confidence": 0.9 },
    "similarity_score": null,
    "created_at": "2026-03-02T10:00:00Z",
    "updated_at": "2026-03-02T10:00:00Z",
    "deduplicated": false
  },
  "meta": { "request_id": "...", "latency_ms": 210 }
}
```

`deduplicated: true` when the server updated an existing record instead of inserting a new one.

---

### POST /v1/memory/semantic/search

Search semantic memory by natural-language query. The server embeds the query and runs cosine similarity search.

```bash
curl -X POST \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/semantic/search \
  -H "Authorization: Bearer mnm_..." \
  -H "Content-Type: application/json" \
  -d '{
    "query": "how does the user like responses formatted?",
    "agent_id": "agent-1",
    "namespace": "preferences",
    "top_k": 5,
    "threshold": 0.75
  }'
```

**Body parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | — | Natural-language search string |
| `agent_id` | string | No | — | Restrict to one agent. Omit for tenant-wide search |
| `namespace` | string | No | — | Restrict to a namespace |
| `top_k` | integer | No | 10 | Maximum results |
| `threshold` | float | No | 0.7 | Minimum cosine similarity (0–1) |
| `metadata_filter` | object | No | — | Exact-match filter on metadata fields |

**Response `200`:**

```json
{
  "data": {
    "results": [
      {
        "id": "a1b2c3d4-...",
        "agent_id": "agent-1",
        "content": "The user prefers concise bullet-point replies.",
        "namespace": "preferences",
        "metadata": {},
        "similarity_score": 0.91,
        "created_at": "2026-03-02T10:00:00Z",
        "updated_at": "2026-03-02T10:00:00Z",
        "deduplicated": false
      }
    ]
  },
  "meta": { "request_id": "...", "latency_ms": 95 }
}
```

---

### GET /v1/memory/semantic/{id}

Retrieve a semantic memory record by UUID.

```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/semantic/a1b2c3d4-... \
  -H "Authorization: Bearer mnm_..."
```

**Response `200`:** Returns a `SemanticResponse` with `similarity_score: null`.
**Error `404`:** Record not found or soft-deleted.

---

### DELETE /v1/memory/semantic/{id}

Soft-delete a semantic memory record. Sets `valid_until` to now — the record is excluded from future searches but not immediately removed from storage.

```bash
curl -X DELETE \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/semantic/a1b2c3d4-... \
  -H "Authorization: Bearer mnm_..."
```

**Response `204`:** No content.
**Error `404`:** Record not found.

---

## Episodic memory

Episodic memory is backed by DynamoDB (hot tier) and S3 (cold tier). Records are immutable after creation.

**Episode types:** `conversation`, `action`, `observation`, `tool_call`

### POST /v1/memory/episodic

Append a time-stamped episode.

```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/episodic \
  -H "Authorization: Bearer mnm_..." \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-1",
    "session_id": "sess-001",
    "type": "conversation",
    "content": { "role": "user", "message": "Summarize the report." },
    "metadata": { "turn": 1 }
  }'
```

**Body parameters:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `agent_id` | string | Yes | Agent identifier |
| `session_id` | string | Yes | Session identifier |
| `type` | string | Yes | One of: `conversation`, `action`, `observation`, `tool_call` |
| `content` | any | Yes | Episode payload — text or JSON object |
| `metadata` | object | No | Arbitrary metadata |

**Response `201`:** Returns an `EpisodeResponse` with a server-assigned `id` and `timestamp`.

---

### GET /v1/memory/episodic/{agent_id}

Query episodes with optional time-range and type filters.

```bash
curl "https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/episodic/agent-1?\
type=conversation&from=2026-03-01T00:00:00Z&to=2026-03-02T23:59:59Z&limit=20" \
  -H "Authorization: Bearer mnm_..."
```

**Query parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Filter to a specific session |
| `type` | string | Filter to an event type |
| `from` | ISO 8601 | Lower bound timestamp (inclusive) |
| `to` | ISO 8601 | Upper bound timestamp (inclusive) |
| `limit` | integer | Maximum episodes to return |

**Response `200`:**

```json
{
  "data": {
    "episodes": [
      {
        "id": "ep_01j...",
        "agent_id": "agent-1",
        "session_id": "sess-001",
        "type": "conversation",
        "content": { "role": "user", "message": "Summarize the report." },
        "metadata": { "turn": 1 },
        "timestamp": "2026-03-02T10:00:00Z"
      }
    ]
  },
  "meta": { "request_id": "...", "latency_ms": 18 }
}
```

---

### GET /v1/memory/episodic/{agent_id}/sessions/{session_id}

Replay all episodes for a session in chronological order.

```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/episodic/agent-1/sessions/sess-001 \
  -H "Authorization: Bearer mnm_..."
```

**Response `200`:** Returns `{ "data": { "episodes": [...] } }` in timestamp order.
**Error `404`:** Session not found.

---

### POST /v1/memory/episodic/{agent_id}/summarize

Compress episodic memory into semantic memories. The API reads episodes for the agent (optionally filtered by session or time range) and inserts summary records into semantic memory.

```bash
curl -X POST \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/episodic/agent-1/summarize \
  -H "Authorization: Bearer mnm_..." \
  -H "Content-Type: application/json" \
  -d '{ "session_id": "sess-001", "namespace": "summaries" }'
```

---

## Unified

### POST /v1/memory

Auto-route a memory store request by payload shape. The server detects whether to store working, semantic, or episodic memory based on which fields are present.

### GET /v1/memory/{agent_id}

Retrieve all memory types for an agent in one call. Returns `{ "state": {...}, "semantic": [...], "episodic": [...] }`.

### POST /v1/memory/search

Search across semantic and episodic memory simultaneously.

```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/search \
  -H "Authorization: Bearer mnm_..." \
  -H "Content-Type: application/json" \
  -d '{ "query": "quarterly report summary", "agent_id": "agent-1", "top_k": 10 }'
```

**Body parameters:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | — | Natural-language search string |
| `agent_id` | string | No | — | Restrict to one agent |
| `top_k` | integer | No | 10 | Maximum results |

**Response `200`:** Returns `SearchResult` objects with a `memory_type` field indicating `"semantic"` or `"episodic"`.

---

### DELETE /v1/memory/{agent_id}

Permanently delete all data for an agent. Removes working memory, semantic memories, episodic records, and S3 objects. This operation is irreversible.

```bash
curl -X DELETE \
  https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/memory/agent-1 \
  -H "Authorization: Bearer mnm_..."
```

**Response `200`:**

```json
{
  "data": {
    "agent_id": "agent-1",
    "deleted": {
      "state": 3,
      "semantic": 47,
      "episodic": 120,
      "s3_objects": 5
    }
  },
  "meta": { "request_id": "...", "latency_ms": 340 }
}
```

---

## Usage

### GET /v1/usage

Retrieve current billing-period metrics.

```bash
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/v1/usage \
  -H "Authorization: Bearer mnm_..."
```

**Response `200`:**

```json
{
  "data": {
    "api_calls_month": 8412,
    "embeddings_generated_month": 1205,
    "storage": { "dynamo_bytes": 2048000, "s3_bytes": 10485760 },
    "agents_count": 12,
    "sessions_count": 87,
    "billing_period": "2026-03"
  },
  "meta": { "request_id": "...", "latency_ms": 22 }
}
```

---

## Error codes

| HTTP status | Code | Meaning |
|-------------|------|---------|
| 400 | `VALIDATION_ERROR` | Request body failed validation. Check field types and required fields |
| 401 | `UNAUTHORIZED` | API key is missing, malformed, or revoked |
| 403 | `FORBIDDEN` | API key is valid but does not have access to the requested resource |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `CONFLICT` | Optimistic lock version mismatch on `PUT /v1/state`. Re-read and retry |
| 413 | `PAYLOAD_TOO_LARGE` | Request body exceeds limit |
| 429 | `RATE_LIMITED` | Request rate exceeds your plan limit. The SDK retries automatically with exponential back-off |
| 500 | `INTERNAL_ERROR` | Server-side error. Retrying is safe |

---

## Rate limits

Rate limits are enforced per API key. The SDK retries `429` and `5xx` responses automatically (up to `max_retries`, default 3) with exponential back-off (0.5s, 1s, 2s).

| Plan | Requests per day |
|------|-----------------|
| Free | 1,000 |
| Starter | 10,000 |
| Pro | 100,000 |
| Scale | 1,000,000 |

Burst limits may apply within a single minute. See [pricing](./pricing.md) for full plan details.
