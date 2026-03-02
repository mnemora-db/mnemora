"""Semantic memory handler — vector search and storage via Aurora pgvector.

Routes:
    POST   /v1/memory/semantic          — store memory (auto-embeds content)
    POST   /v1/memory/semantic/search   — vector similarity search
    GET    /v1/memory/semantic/{id}     — retrieve memory by UUID
    DELETE /v1/memory/semantic/{id}     — soft-delete memory by UUID

All requests are dispatched from a single Lambda triggered by the
API Gateway ``{proxy+}`` catch-all route under ``/v1/memory/semantic``.
Routing is done by parsing the HTTP method and path segments from the
event's requestContext.

Tenant isolation:
    ``tenant_id`` is ALWAYS derived from the Lambda authorizer context
    (``event["requestContext"]["authorizer"]["lambda"]["tenantId"]``).
    Client-supplied tenant values are never trusted.

Deduplication:
    On create, an existing memory with cosine similarity > 0.95 in the
    same tenant/agent scope is updated in-place rather than creating a
    new row.  The response field ``deduplicated=True`` signals this.

Chunking:
    Content longer than ~8 000 tokens is split into overlapping chunks.
    Each chunk is stored as a separate row linked by a shared ``parent_id``
    in metadata.  The response describes all chunks via ``chunk_count``.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from lib.responses import error_response, success_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Approximate tokens-per-character ratio used for chunking threshold.
_CHARS_PER_TOKEN: int = 4
_MAX_TOKENS: int = 8_000


# ---------------------------------------------------------------------------
# Public handler entrypoint
# ---------------------------------------------------------------------------


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle semantic memory requests.

    Args:
        event: API Gateway HTTP API v2 event payload.
        context: Lambda execution context (unused; retained for signature).

    Returns:
        API Gateway-compatible response dict.
    """
    start_time = time.time()
    request_id = _extract_request_id(event)
    http_ctx = event.get("requestContext", {}).get("http", {})
    method = http_ctx.get("method", "UNKNOWN")
    path = http_ctx.get("path", "")
    tenant_id = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("lambda", {})
        .get("tenantId", "unknown")
    )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": path,
                "method": method,
                "handler": "semantic",
            }
        )
    )

    try:
        # Segments after stripping /v1/memory/semantic prefix.
        # Full path: /v1/memory/semantic[/search|/<id>]
        full_segments = [s for s in path.strip("/").split("/") if s]
        # Drop the leading ["v1", "memory", "semantic"] prefix.
        segments = full_segments[3:]

        if method == "POST":
            if len(segments) == 1 and segments[0] == "search":
                return _handle_search(event, tenant_id, request_id, start_time)
            if len(segments) == 0:
                return _handle_create(event, tenant_id, request_id, start_time)

        if method == "GET" and len(segments) == 1:
            return _handle_get(tenant_id, segments[0], request_id, start_time)

        if method == "DELETE" and len(segments) == 1:
            return _handle_delete(tenant_id, segments[0], request_id, start_time)

        return error_response(
            message=f"Not found: {method} {path}",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    except Exception:
        logger.exception(
            "Unhandled error in semantic handler",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )
        return error_response(
            message="Internal server error",
            status=500,
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        )


# ---------------------------------------------------------------------------
# Path / body helpers
# ---------------------------------------------------------------------------


def _extract_request_id(event: dict[str, Any]) -> str:
    """Extract request_id from API Gateway event context.

    Args:
        event: API Gateway HTTP API v2 event payload.

    Returns:
        The requestId string, or 'unknown' if absent.
    """
    return event.get("requestContext", {}).get("requestId", "unknown")


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """Decode the JSON request body.

    Args:
        event: API Gateway HTTP API v2 event payload.

    Returns:
        Parsed body dict.  Empty dict when there is no body.

    Raises:
        json.JSONDecodeError: Body is not valid JSON.
        TypeError: Body is not a string.
    """
    body_str = event.get("body") or ""
    if not body_str:
        return {}
    return json.loads(body_str)


def _row_to_response(
    row: dict[str, Any],
    *,
    similarity_score: float | None = None,
    deduplicated: bool = False,
) -> dict[str, Any]:
    """Convert a ``semantic_memory`` database row to a response dict.

    Args:
        row: Dict returned by psycopg ``dict_row`` factory.
        similarity_score: Cosine similarity from a search query, if any.
        deduplicated: True when an existing row was updated instead of
            a new row being inserted.

    Returns:
        Dict matching the ``SemanticResponse`` shape.
    """

    def _dt_to_iso(val: Any) -> str:
        if val is None:
            return ""
        if isinstance(val, str):
            return val
        if isinstance(val, datetime):
            return val.isoformat()
        return str(val)

    return {
        "id": str(row["id"]),
        "agent_id": row["agent_id"],
        "content": row["content"],
        "namespace": row["namespace"],
        "metadata": row.get("metadata") or {},
        "similarity_score": similarity_score,
        "created_at": _dt_to_iso(row.get("created_at")),
        "updated_at": _dt_to_iso(row.get("updated_at")),
        "deduplicated": deduplicated,
    }


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


def _handle_create(
    event: dict[str, Any],
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """POST /v1/memory/semantic — store content with auto-generated embedding.

    Performs deduplication: if an existing memory for the same
    tenant/agent has cosine similarity > 0.95 with the incoming content,
    that row is updated in-place and ``deduplicated=True`` is returned.

    For content exceeding ~8 000 tokens, the text is split into overlapping
    chunks and each chunk is stored as a separate row linked by a shared
    ``parent_id`` in their metadata.

    Args:
        event: API Gateway HTTP API v2 event payload.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        201 Created with SemanticResponse, or 200 when deduplicated.
    """
    from pydantic import ValidationError

    from lib.aurora import get_connection, set_tenant_context
    from lib.embeddings import generate_embedding, generate_embeddings_chunked
    from lib.models import SemanticCreateRequest

    try:
        body = _parse_body(event)
    except (json.JSONDecodeError, TypeError):
        return error_response(
            message="Invalid JSON in request body",
            status=400,
            error_code="INVALID_JSON",
            request_id=request_id,
        )

    try:
        req = SemanticCreateRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    estimated_tokens = len(req.content) // _CHARS_PER_TOKEN

    if estimated_tokens > _MAX_TOKENS:
        # --- Chunked path ---
        chunks = generate_embeddings_chunked(req.content)
        parent_id = str(uuid.uuid4())
        chunk_count = len(chunks)
        first_row: dict[str, Any] | None = None

        with get_connection() as conn:
            set_tenant_context(conn, tenant_id)
            for idx, (chunk_text, chunk_embedding) in enumerate(chunks):
                chunk_metadata = {
                    **req.metadata,
                    "parent_id": parent_id,
                    "chunk_index": idx,
                    "chunk_count": chunk_count,
                    "chunked": True,
                }
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO semantic_memory
                            (tenant_id, agent_id, namespace, content,
                             embedding, metadata)
                        VALUES (%s, %s, %s, %s, %s::vector, %s::jsonb)
                        RETURNING
                            id, agent_id, namespace, content, metadata,
                            created_at, updated_at
                        """,
                        (
                            tenant_id,
                            req.agent_id,
                            req.namespace,
                            chunk_text,
                            str(chunk_embedding),
                            json.dumps(chunk_metadata),
                        ),
                    )
                    row = cur.fetchone()

                if first_row is None and row is not None:
                    first_row = dict(row)

        logger.info(
            json.dumps(
                {
                    "request_id": request_id,
                    "tenant_id": tenant_id,
                    "agent_id": req.agent_id,
                    "action": "semantic_create_chunked",
                    "chunk_count": chunk_count,
                    "latency_ms": round((time.time() - start_time) * 1000),
                }
            )
        )

        if first_row is None:
            return error_response(
                message="Internal server error",
                status=500,
                error_code="INTERNAL_ERROR",
                request_id=request_id,
            )

        response_data = _row_to_response(first_row, deduplicated=False)
        response_data["metadata"] = {
            **response_data["metadata"],
            "chunk_count": chunk_count,
            "chunked": True,
        }
        return success_response(
            body=response_data,
            status=201,
            request_id=request_id,
            start_time=start_time,
        )

    # --- Normal (single-chunk) path ---
    embedding = generate_embedding(req.content)
    embedding_str = str(embedding)

    with get_connection() as conn:
        set_tenant_context(conn, tenant_id)

        # Deduplication check: cosine similarity > 0.95 in same tenant/agent.
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, content, metadata, created_at, updated_at
                FROM semantic_memory
                WHERE tenant_id = %s
                  AND agent_id = %s
                  AND NOT is_deleted
                  AND 1 - (embedding <=> %s::vector) > 0.95
                ORDER BY 1 - (embedding <=> %s::vector) DESC
                LIMIT 1
                """,
                (tenant_id, req.agent_id, embedding_str, embedding_str),
            )
            existing = cur.fetchone()

        if existing is not None:
            # Update the duplicate in-place.
            merged_metadata = {**(existing["metadata"] or {}), **req.metadata}
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE semantic_memory
                    SET content    = %s,
                        embedding  = %s::vector,
                        metadata   = %s::jsonb,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING
                        id, agent_id, namespace, content, metadata,
                        created_at, updated_at
                    """,
                    (
                        req.content,
                        embedding_str,
                        json.dumps(merged_metadata),
                        existing["id"],
                    ),
                )
                updated_row = cur.fetchone()

            logger.info(
                json.dumps(
                    {
                        "request_id": request_id,
                        "tenant_id": tenant_id,
                        "agent_id": req.agent_id,
                        "action": "semantic_deduplicated",
                        "latency_ms": round((time.time() - start_time) * 1000),
                    }
                )
            )

            row_data = dict(updated_row) if updated_row else {}
            return success_response(
                body=_row_to_response(row_data, deduplicated=True),
                status=200,
                request_id=request_id,
                start_time=start_time,
            )

        # New memory — INSERT.
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO semantic_memory
                    (tenant_id, agent_id, namespace, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s::vector, %s::jsonb)
                RETURNING
                    id, agent_id, namespace, content, metadata,
                    created_at, updated_at
                """,
                (
                    tenant_id,
                    req.agent_id,
                    req.namespace,
                    req.content,
                    embedding_str,
                    json.dumps(req.metadata),
                ),
            )
            new_row = cur.fetchone()

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": req.agent_id,
                "action": "semantic_created",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    row_data = dict(new_row) if new_row else {}
    return success_response(
        body=_row_to_response(row_data, deduplicated=False),
        status=201,
        request_id=request_id,
        start_time=start_time,
    )


def _handle_search(
    event: dict[str, Any],
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """POST /v1/memory/semantic/search — vector similarity search.

    Embeds the query text and retrieves the top-K most similar memories
    above the configured similarity threshold.  Optional filters narrow
    the search by agent_id, namespace, or JSONB metadata containment.

    Args:
        event: API Gateway HTTP API v2 event payload.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with ``{"results": [...], "count": N}``.
    """
    from pydantic import ValidationError

    from lib.aurora import get_connection, set_tenant_context
    from lib.embeddings import generate_embedding
    from lib.models import SemanticSearchRequest

    try:
        body = _parse_body(event)
    except (json.JSONDecodeError, TypeError):
        return error_response(
            message="Invalid JSON in request body",
            status=400,
            error_code="INVALID_JSON",
            request_id=request_id,
        )

    try:
        req = SemanticSearchRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    query_embedding = generate_embedding(req.query)
    embedding_str = str(query_embedding)

    # Build the query and params list dynamically to avoid string interpolation.
    query_parts = [
        """
        SELECT id, agent_id, content, namespace, metadata,
               1 - (embedding <=> %s::vector) AS similarity,
               created_at, updated_at
        FROM semantic_memory
        WHERE tenant_id = %s
          AND NOT is_deleted
          AND 1 - (embedding <=> %s::vector) > %s
        """
    ]
    params: list[Any] = [embedding_str, tenant_id, embedding_str, req.threshold]

    if req.agent_id is not None:
        query_parts.append("AND agent_id = %s")
        params.append(req.agent_id)

    if req.namespace is not None:
        query_parts.append("AND namespace = %s")
        params.append(req.namespace)

    if req.metadata_filter is not None:
        query_parts.append("AND metadata @> %s::jsonb")
        params.append(json.dumps(req.metadata_filter))

    query_parts.append("ORDER BY similarity DESC LIMIT %s")
    params.append(req.top_k)

    full_query = "\n".join(query_parts)

    with get_connection() as conn:
        set_tenant_context(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute(full_query, tuple(params))
            rows = cur.fetchall()

    results = [
        _row_to_response(dict(row), similarity_score=float(row["similarity"]))
        for row in rows
    ]

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": req.agent_id,
                "action": "semantic_search",
                "result_count": len(results),
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body={"results": results, "count": len(results)},
        request_id=request_id,
        start_time=start_time,
    )


def _handle_get(
    tenant_id: str,
    memory_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """GET /v1/memory/semantic/{id} — retrieve a single memory by UUID.

    Args:
        tenant_id: Tenant identifier from the Lambda authorizer.
        memory_id: UUID of the memory to retrieve (path parameter).
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with SemanticResponse on success, 404 if not found.
    """
    from lib.aurora import get_connection, set_tenant_context

    with get_connection() as conn:
        set_tenant_context(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, agent_id, content, namespace, metadata,
                       created_at, updated_at
                FROM semantic_memory
                WHERE id = %s::uuid
                  AND tenant_id = %s
                  AND NOT is_deleted
                """,
                (memory_id, tenant_id),
            )
            row = cur.fetchone()

    if row is None:
        return error_response(
            message=f"Memory '{memory_id}' not found",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "action": "semantic_get",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body=_row_to_response(dict(row)),
        request_id=request_id,
        start_time=start_time,
    )


def _handle_delete(
    tenant_id: str,
    memory_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """DELETE /v1/memory/semantic/{id} — soft-delete a memory by UUID.

    Sets ``is_deleted = TRUE`` and bumps ``updated_at`` on the target row.
    Returns 404 when the row does not exist or is already deleted.

    Args:
        tenant_id: Tenant identifier from the Lambda authorizer.
        memory_id: UUID of the memory to soft-delete (path parameter).
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        204 (no content) on success, 404 if not found.
    """
    from lib.aurora import get_connection, set_tenant_context

    with get_connection() as conn:
        set_tenant_context(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE semantic_memory
                SET is_deleted = TRUE,
                    updated_at = NOW()
                WHERE id = %s::uuid
                  AND tenant_id = %s
                  AND NOT is_deleted
                RETURNING id
                """,
                (memory_id, tenant_id),
            )
            deleted_row = cur.fetchone()

    if deleted_row is None:
        return error_response(
            message=f"Memory '{memory_id}' not found",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "action": "semantic_delete",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    # 204 No Content — body is None; meta.request_id still included by helper.
    return success_response(
        body=None,
        status=204,
        request_id=request_id,
        start_time=start_time,
    )
