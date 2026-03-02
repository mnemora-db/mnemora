-- Migration 001: Initial semantic_memory schema with pgvector
-- Creates the semantic_memory table, HNSW indexes, and row-level security.
--
-- Access patterns served:
--   1. Vector similarity search by tenant + agent (idx_semantic_embedding, idx_semantic_tenant_agent)
--   2. Namespace-scoped vector search (idx_semantic_namespace)
--   3. Metadata-filtered queries via JSONB containment (idx_semantic_metadata)
--
-- HNSW parameters: m=16, ef_construction=200 — minimum production values.
--   m=16 → each node connects to 16 neighbors (good recall/speed trade-off for 1024-dim vectors)
--   ef_construction=200 → build-time search breadth (higher = better recall, slower build)
--
-- RLS policy: tenant_isolation requires SET app.tenant_id before every query.

BEGIN;

-- Enable pgvector extension for vector(1024) column type and HNSW indexes.
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable uuid-ossp for uuid_generate_v4() default on the id column.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Semantic memory: stores embeddings alongside content and metadata.
-- One row per memory fragment. Soft-deleted rows (is_deleted=TRUE) are
-- excluded from partial indexes to keep them lean.
CREATE TABLE IF NOT EXISTS semantic_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    namespace TEXT NOT NULL DEFAULT 'default',
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index: tenant + agent lookups excluding soft-deleted rows.
-- Serves: GET /v1/memory/semantic/{id}, list by agent, dedup checks.
CREATE INDEX IF NOT EXISTS idx_semantic_tenant_agent
    ON semantic_memory(tenant_id, agent_id) WHERE NOT is_deleted;

-- Index: HNSW for cosine-distance vector similarity search.
-- Serves: POST /v1/memory/semantic/search — the primary vector search endpoint.
-- Note: Cannot use CREATE INDEX CONCURRENTLY inside a transaction.
-- For the initial empty-table migration this is acceptable. Future index
-- rebuilds on live data MUST use CONCURRENTLY outside a transaction.
CREATE INDEX IF NOT EXISTS idx_semantic_embedding
    ON semantic_memory USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- Index: GIN on metadata JSONB for containment queries (@>).
-- Serves: filtered search where callers pass metadata predicates
-- e.g. WHERE metadata @> '{"source": "wiki"}'.
CREATE INDEX IF NOT EXISTS idx_semantic_metadata
    ON semantic_memory USING gin (metadata);

-- Index: namespace-scoped lookups excluding soft-deleted rows.
-- Serves: POST /v1/memory/semantic/search with namespace filter.
CREATE INDEX IF NOT EXISTS idx_semantic_namespace
    ON semantic_memory(tenant_id, namespace) WHERE NOT is_deleted;

-- Row-Level Security: defense-in-depth tenant isolation.
-- Even if application code has a bug, RLS prevents cross-tenant data leakage.
-- The app must call SET app.tenant_id = <tenant_id> on every connection.
ALTER TABLE semantic_memory ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    DROP POLICY IF EXISTS tenant_isolation ON semantic_memory;
END
$$;

CREATE POLICY tenant_isolation ON semantic_memory
    USING (tenant_id = current_setting('app.tenant_id', true));

-- Migration tracking table: records which migration files have been applied.
-- The run_migration.py runner checks this before executing each .sql file.
CREATE TABLE IF NOT EXISTS _migrations (
    id SERIAL PRIMARY KEY,
    filename TEXT NOT NULL UNIQUE,
    applied_at TIMESTAMPTZ DEFAULT NOW()
);

COMMIT;
