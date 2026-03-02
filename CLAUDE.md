# CLAUDE.md — Mnemora Project

## What is Mnemora?

Mnemora is an AWS-native, serverless database for AI agent memory. One API for four memory types: working (key-value state), semantic (vector search), episodic (time-series logs), procedural (relational schemas). Built on DynamoDB + Aurora Serverless v2 (pgvector) + S3 + Lambda.

## Why does it exist?

AI agents need persistent memory across sessions. Today developers stitch together 3-5 separate databases (Redis for state, Pinecone for vectors, Postgres for relational, S3 for logs). Mnemora unifies this into a single managed service with native integrations for LangChain, LangGraph, CrewAI, and AutoGen.

## Project structure

```
mnemora/
├── CLAUDE.md                    # This file — Mnemora project brain
├── infra/                       # AWS CDK stack (TypeScript)
│   ├── bin/mnemora.ts           # CDK app entry
│   ├── lib/
│   │   ├── mnemora-stack.ts     # Main stack: DynamoDB, Aurora, S3, Lambda, API GW
│   │   ├── auth-stack.ts       # API key auth + Lambda authorizer
│   │   └── monitoring-stack.ts # CloudWatch dashboards + alarms
│   ├── cdk.json
│   ├── tsconfig.json
│   └── package.json
├── api/                         # Lambda handlers (Python)
│   ├── handlers/
│   │   ├── state.py            # Working memory CRUD (DynamoDB)
│   │   ├── semantic.py         # Semantic memory + vector search (Aurora pgvector)
│   │   ├── episodic.py         # Episodic memory + time-range queries
│   │   ├── unified.py          # Unified /v1/memory endpoint
│   │   ├── auth.py             # API key authorizer
│   │   └── health.py           # Health check
│   ├── lib/
│   │   ├── dynamo.py           # DynamoDB client wrapper
│   │   ├── aurora.py           # Aurora/pgvector client wrapper
│   │   ├── embeddings.py       # Bedrock Titan embeddings
│   │   ├── s3.py               # S3 episodic storage
│   │   └── models.py           # Pydantic models for all memory types
│   ├── requirements.txt
│   └── tests/
│       ├── test_state.py
│       ├── test_semantic.py
│       ├── test_episodic.py
│       └── test_integration.py
├── sdk/                         # Python SDK (published to PyPI as mnemora-sdk)
│   ├── mnemora/
│   │   ├── __init__.py
│   │   ├── client.py           # Main Mnemora client
│   │   ├── state.py            # Working memory operations
│   │   ├── semantic.py         # Semantic memory operations
│   │   ├── episodic.py         # Episodic memory operations
│   │   └── integrations/
│   │       ├── langgraph.py    # LangGraph CheckpointSaver
│   │       ├── langchain.py    # LangChain Memory class
│   │       └── crewai.py       # CrewAI Storage backend
│   ├── pyproject.toml
│   └── tests/
├── dashboard/                   # Next.js dashboard (deployed on Vercel)
│   ├── app/
│   ├── components/
│   └── package.json
├── docs/                        # Documentation site
│   └── ...
└── examples/                    # Example agents
    ├── langgraph-chatbot/
    ├── crewai-researcher/
    └── basic-memory/
```

## Tech stack

| Layer | Technology | Why |
|-------|-----------|-----|
| IaC | AWS CDK (TypeScript) | Best L2 constructs for Aurora + Lambda + DynamoDB |
| API handlers | Python 3.12 on Lambda ARM64 | LangChain/CrewAI ecosystem is Python-first |
| API Gateway | HTTP API (not REST API) | $1/M requests vs $3.50/M |
| Working memory | DynamoDB (on-demand) | Sub-10ms key-value, native TTL |
| Semantic memory | Aurora Serverless v2 + pgvector | Vector search + relational in one engine |
| Episodic memory | DynamoDB (hot) + S3 (cold) | Cost-effective tiered storage |
| Embeddings | Bedrock Titan Text Embeddings v2 | $0.02/M tokens, 1024 dims |
| SDK | Python (PyPI: mnemora-sdk) | Native for LangChain/CrewAI/AutoGen |
| Dashboard | Next.js on Vercel | Fast deploy, GitHub OAuth |
| Monitoring | CloudWatch | AWS-native, no extra cost |

## Commands

```bash
# Infrastructure
cd infra && npx cdk deploy          # Deploy all AWS resources
cd infra && npx cdk diff            # Preview changes
cd infra && npx cdk destroy         # Tear down

# API (local testing)
cd api && pip install -r requirements.txt
cd api && python -m pytest tests/ -v

# SDK
cd sdk && pip install -e .
cd sdk && python -m pytest tests/ -v

# Dashboard
cd dashboard && npm install && npm run dev

# Linting
cd api && ruff check . && ruff format .
cd sdk && ruff check . && ruff format .
cd infra && npx tsc --noEmit
cd dashboard && npx tsc --noEmit
```

## Code conventions

- Python: Use ruff for linting+formatting. Type hints everywhere. Pydantic v2 for all models.
- TypeScript: Strict mode. No `any` types.
- All API responses follow: `{ "data": ..., "meta": { "request_id": "...", "latency_ms": N } }`
- All errors follow: `{ "error": { "code": "...", "message": "..." }, "meta": { ... } }`
- HTTP status codes: 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 409 Conflict, 413 Payload Too Large, 429 Too Many Requests, 500 Internal Server Error.
- Every handler logs: request_id, tenant_id, agent_id, latency_ms, status_code.
- Never log: API keys, memory content, PII.

## DynamoDB schema

Single-table design. All items share one table: `mnemora-state`.

```
PK (partition key): tenant_id#agent_id
SK (sort key): varies by entity type

State items:     SK = SESSION#<session_id>
Agent metadata:  SK = META
Episodes (hot):  SK = EPISODE#<ISO8601_timestamp>#<episode_id>
API keys:        PK = APIKEY#<sha256_hash>, SK = META
```

Every item has: `created_at`, `updated_at`, `ttl` (Unix timestamp, 0 = no expiry).
State items have: `version` (integer for optimistic locking).

## Aurora pgvector schema

Database: `mnemora`, schema per tenant or shared with RLS.

```sql
-- Semantic memory
CREATE TABLE semantic_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    namespace TEXT DEFAULT 'default',
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 1.0,
    valid_from TIMESTAMPTZ DEFAULT now(),
    valid_until TIMESTAMPTZ,  -- NULL = currently valid
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_semantic_embedding ON semantic_memory
    USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 200);
CREATE INDEX idx_semantic_tenant_agent ON semantic_memory (tenant_id, agent_id);
CREATE INDEX idx_semantic_namespace ON semantic_memory (tenant_id, agent_id, namespace);

-- LangGraph checkpoints (compatible with langgraph-checkpoint-postgres)
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now(),
    ttl TIMESTAMPTZ,  -- OUR ADDITION: auto-cleanup
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);

CREATE TABLE checkpoint_blobs (
    thread_id TEXT NOT NULL,
    checkpoint_ns TEXT NOT NULL DEFAULT '',
    channel TEXT NOT NULL,
    version TEXT NOT NULL,
    type TEXT NOT NULL,
    blob BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, channel, version)
);

CREATE TABLE checkpoint_writes (
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

-- Procedural memory (tool definitions, schemas, logic)
CREATE TABLE procedural_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('tool', 'schema', 'prompt', 'rule')),
    definition JSONB NOT NULL,
    version INTEGER DEFAULT 1,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_id, agent_id, name, version)
);
```

## API endpoints

All endpoints prefixed with `/v1/`. Auth via `Authorization: Bearer <api_key>` header.

```
# Health
GET  /v1/health

# Working memory (DynamoDB)
POST   /v1/state                           # Store agent state
GET    /v1/state/{agent_id}                # Get current state
GET    /v1/state/{agent_id}/sessions       # List sessions
PUT    /v1/state/{agent_id}                # Update (optimistic lock)
DELETE /v1/state/{agent_id}/{session_id}   # Delete session

# Semantic memory (pgvector)
POST   /v1/memory/semantic                 # Store (auto-embeds)
POST   /v1/memory/semantic/search          # Vector similarity search
GET    /v1/memory/semantic/{id}            # Get by ID
DELETE /v1/memory/semantic/{id}            # Soft delete (set valid_until)

# Episodic memory (DynamoDB hot + S3 cold)
POST   /v1/memory/episodic                 # Store episode
GET    /v1/memory/episodic/{agent_id}      # Query (time range + filters)
GET    /v1/memory/episodic/{agent_id}/sessions/{session_id}  # Session replay
POST   /v1/memory/episodic/{agent_id}/summarize  # Summarize to semantic

# Unified
POST   /v1/memory                          # Auto-route by payload shape
GET    /v1/memory/{agent_id}               # All memory types for agent
POST   /v1/memory/search                   # Cross-memory search
DELETE /v1/memory/{agent_id}               # Purge all (GDPR)

# Usage
GET    /v1/usage                           # Current billing period metrics
```

## Embedding pipeline

When storing semantic memory:

1. Client sends `POST /v1/memory/semantic` with `{ content: "...", agent_id: "...", metadata: {...} }`
2. Handler calls Bedrock Titan: `bedrock.invoke_model(modelId="amazon.titan-embed-text-v2:0", body={ inputText, dimensions: 1024 })`
3. Receives 1024-dim float array
4. Deduplication check: search pgvector for cosine similarity > 0.95 with same tenant+agent
5. If duplicate found: UPDATE existing record (bump `updated_at`, merge metadata)
6. If new: INSERT with embedding
7. Return memory ID to client

For large/batch payloads: enqueue to SQS, process async, return `202 Accepted` with status URL.

## Multi-tenancy

All tenant isolation is logical, not physical:

- **DynamoDB:** PK prefix `TENANT#<id>` ensures partition isolation
- **Aurora:** `tenant_id` column + parameterized queries (RLS for defense-in-depth)
- **S3:** Prefix `s3://mnemora-data/<tenant_id>/`
- **Lambda authorizer:** API key → tenant_id mapping, injected into all downstream calls
- **NEVER** trust client-provided tenant_id. Always derive from API key.

## Error handling

Every Lambda handler wraps execution in try/except:

```python
def handler(event, context):
    request_id = event["requestContext"]["requestId"]
    try:
        # ... business logic ...
        return {"statusCode": 200, "body": json.dumps({"data": result, "meta": {"request_id": request_id}})}
    except ValidationError as e:
        return {"statusCode": 400, "body": json.dumps({"error": {"code": "VALIDATION_ERROR", "message": str(e)}})}
    except ConditionalCheckFailedException:
        return {"statusCode": 409, "body": json.dumps({"error": {"code": "CONFLICT", "message": "Version conflict"}})}
    except Exception as e:
        logger.error(f"Unhandled error: {e}", extra={"request_id": request_id})
        return {"statusCode": 500, "body": json.dumps({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}})}
```

## Testing strategy

- Unit tests: Mock AWS services with moto (DynamoDB) and pytest fixtures (Aurora)
- Integration tests: Deploy to staging, run against real AWS resources
- Load tests: Artillery targeting deployed API
- SDK tests: Test against local API server (LocalStack or deployed staging)
- Every PR must pass: `ruff check`, `pytest`, `tsc --noEmit`

## Key dependencies

```
# API (Python)
boto3>=1.35.0          # AWS SDK
psycopg[binary]>=3.2   # PostgreSQL (pgvector)
pydantic>=2.0          # Validation
mangum>=0.19           # Lambda ASGI adapter (if using FastAPI)

# SDK (Python)
httpx>=0.27            # Async HTTP client
pydantic>=2.0

# Infra (TypeScript)
aws-cdk-lib>=2.170     # CDK
constructs>=10.0
```

## Competitor context

When making architectural decisions, know what competitors do:

- **Mem0:** Memory SDK, requires LLM call per operation, wraps external DBs, no checkpoint support. 43K GitHub stars.
- **Zep/Graphiti:** Temporal knowledge graph, bi-temporal data model, closed-source platform (only Graphiti OSS). Sub-200ms retrieval.
- **Letta/MemGPT:** Self-editing memory blocks, core vs archival memory tiers, heavy server requirement, not serverless. 42K stars.
- **LangGraph checkpointer:** Our #1 integration target. Schema in `checkpoint_postgres` package. Must be compatible.

Our differentiation: serverless, unified memory types, no mandatory LLM dependency, AWS-native, LangGraph-compatible with TTL cleanup.

## Brand & Design System

Mnemora's visual identity follows a Vercel-inspired design philosophy: Swiss precision, dark-first, monochrome dominance with surgical teal accent.

**Colors:**
- Background: `#09090B` (primary), `#111114` (surface), `#18181B` (cards)
- Text: `#FAFAFA` (primary), `#A1A1AA` (secondary), `#71717A` (tertiary)
- Accent: `#2DD4BF` (teal-400) — used ONLY for interactive elements, links, and the logo mark
- Borders: `#27272A` (subtle), `#3F3F46` (default)

**Typography:** Geist Sans (body) + Geist Mono (code). Both are open-source OFL.

**Voice:** Direct, technical, second person. "Your agent remembers" not "Our system enables memory persistence."

**Logo:** Abstract "M" / neural pathway mark + "mnemora" lowercase wordmark in Geist Sans weight 600.

For the full design system, see `docs/brand/design-system.md`.

## What Claude should NOT do

- Never build a custom database engine. Use DynamoDB and Aurora.
- Never add Neo4j or graph database dependency. Use Postgres for relationships.
- Never require an LLM call for basic CRUD operations.
- Never use REST API Gateway (use HTTP API — 71% cheaper).
- Never use x86 Lambda (use ARM64/Graviton — 20% cheaper).
- Never use `WidthType.PERCENTAGE` in any generated documents.
- Never store API keys in plaintext. SHA-256 hash before storing in DynamoDB.
- Never trust client-provided tenant_id. Always derive from authenticated API key.
- Never log memory content or API keys.

## What Claude should ALWAYS do

- Run `ruff check` and `ruff format` after editing Python files.
- Run `npx tsc --noEmit` after editing TypeScript files.
- Run `pytest` after changing handler logic.
- Add type hints to all Python functions.
- Use Pydantic models for request/response validation.
- Include `request_id` in all API responses and logs.
- Use parameterized queries for all database operations (never string interpolation).
- Add CloudWatch metrics for latency, error rate, and DynamoDB consumed capacity.
- Write docstrings for all public functions.
- Commit after each completed task step with descriptive message.

## Development workflow

1. Plan the change (what files, what tests)
2. Write/update tests first
3. Implement the change
4. Run linting: `ruff check . && ruff format .`
5. Run tests: `pytest tests/ -v`
6. Verify CDK synth: `cd infra && npx cdk synth --quiet`
7. Commit with descriptive message
8. If deploying: `cd infra && npx cdk deploy --require-approval never`

## Reference docs

For detailed specs beyond this file:

- Aurora pgvector: see `docs/architecture/pgvector.md`
- DynamoDB access patterns: see `docs/architecture/dynamodb.md`
- LangGraph integration: see `sdk/mnemora/integrations/langgraph.py` docstring
- API OpenAPI spec: see `docs/api/openapi.yaml`
- Deployment runbook: see `docs/ops/deployment.md`
