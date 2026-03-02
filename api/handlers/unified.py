"""Unified memory handler — auto-routes across all memory types.

Routes:
    POST   /v1/memory              — auto-detect type and store
    GET    /v1/memory/{agent_id}   — combined view across all stores
    POST   /v1/memory/search       — cross-memory search
    DELETE /v1/memory/{agent_id}   — GDPR purge across all stores
    GET    /v1/usage               — per-tenant usage stats

All requests are dispatched from a single Lambda triggered by the
API Gateway ``{proxy+}`` catch-all route under ``/v1/memory`` and
``/v1/usage``.

Tenant isolation:
    ``tenant_id`` is ALWAYS derived from the Lambda authorizer context
    (``event["requestContext"]["authorizer"]["lambda"]["tenantId"]``).
    Client-supplied tenant values are never trusted.

Auto-routing rules for POST /v1/memory (evaluated in order):
    1. Payload has ``data`` (dict) and ``session_id`` (str) → working memory
    2. Payload has ``content`` (str) and ``type`` in episode types → episodic
    3. Payload has ``content`` (str) and no ``type`` → semantic memory
    4. Otherwise → 400 with helpful message

Partial failures:
    GET /v1/memory/{agent_id} fetches from all three stores in sequence.
    If an individual store fails, partial data is returned with a ``warnings``
    list rather than failing the entire request.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from lib.responses import error_response, success_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Episode types that trigger episodic routing in POST /v1/memory.
_EPISODE_TYPES = frozenset({"conversation", "action", "observation", "tool_call"})


# ---------------------------------------------------------------------------
# Public handler entrypoint
# ---------------------------------------------------------------------------


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle unified memory and usage requests.

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
                "handler": "unified",
            }
        )
    )

    try:
        # Segments after /v1/memory or /v1/usage prefix.
        full_segments = [s for s in path.strip("/").split("/") if s]

        # GET /v1/usage  (path: /v1/usage → segments: ["v1", "usage"])
        if method == "GET" and len(full_segments) >= 2 and full_segments[1] == "usage":
            return _handle_usage(tenant_id, request_id, start_time)

        # All remaining routes are under /v1/memory.
        # Drop ["v1", "memory"] prefix to get sub-segments.
        memory_segments = full_segments[2:] if len(full_segments) >= 2 else []

        # POST /v1/memory/search  (must check before generic agent_id route)
        if (
            method == "POST"
            and len(memory_segments) == 1
            and memory_segments[0] == "search"
        ):
            return _handle_search(event, tenant_id, request_id, start_time)

        # POST /v1/memory — auto-route by payload shape
        if method == "POST" and len(memory_segments) == 0:
            return _handle_create(event, tenant_id, request_id, start_time)

        # GET /v1/memory/{agent_id}
        if method == "GET" and len(memory_segments) == 1:
            return _handle_get_agent(
                tenant_id, memory_segments[0], request_id, start_time
            )

        # DELETE /v1/memory/{agent_id}
        if method == "DELETE" and len(memory_segments) == 1:
            return _handle_purge(tenant_id, memory_segments[0], request_id, start_time)

        return error_response(
            message=f"Not found: {method} {path}",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    except Exception:
        logger.exception(
            "Unhandled error in unified handler",
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
        Parsed body dict. Empty dict when there is no body.

    Raises:
        json.JSONDecodeError: Body is not valid JSON.
        TypeError: Body is not a string.
    """
    body_str = event.get("body") or ""
    if not body_str:
        return {}
    return json.loads(body_str)


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


def _handle_create(
    event: dict[str, Any],
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """POST /v1/memory — auto-detect memory type and route.

    Routing order:
    1. ``data`` (dict) + ``session_id``  → working memory (state)
    2. ``content`` (str) + ``type`` in episode types → episodic memory
    3. ``content`` (str) without ``type`` → semantic memory
    4. Otherwise → 400

    Args:
        event: API Gateway HTTP API v2 event payload.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        201 Created with the stored memory and ``memory_type`` field.
    """
    from pydantic import ValidationError  # noqa: PLC0415

    from lib.models import UnifiedMemoryCreateRequest  # noqa: PLC0415

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
        req = UnifiedMemoryCreateRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    # --- Routing decision ---
    has_data = req.data is not None
    has_session = req.session_id is not None
    has_content = req.content is not None
    has_type = req.type is not None

    if has_data and has_session:
        return _route_to_state(req, tenant_id, request_id, start_time)

    if has_content and has_type:
        if req.type not in _EPISODE_TYPES:
            return error_response(
                message=(
                    f"Unknown episode type '{req.type}'. "
                    f"Expected one of: {', '.join(sorted(_EPISODE_TYPES))}"
                ),
                status=400,
                error_code="VALIDATION_ERROR",
                request_id=request_id,
            )
        return _route_to_episodic(req, tenant_id, request_id, start_time)

    if has_content and not has_type:
        if not isinstance(req.content, str):
            return error_response(
                message=(
                    "Semantic memory requires 'content' to be a string. "
                    "Got a dict — did you mean to include a 'type' field "
                    "for episodic memory?"
                ),
                status=400,
                error_code="VALIDATION_ERROR",
                request_id=request_id,
            )
        return _route_to_semantic(req, tenant_id, request_id, start_time)

    return error_response(
        message=(
            "Cannot determine memory type from payload. "
            "For working memory: provide 'data' (dict) and 'session_id'. "
            "For episodic memory: provide 'content' (str) and 'type' "
            "(conversation|action|observation|tool_call). "
            "For semantic memory: provide 'content' (str) without 'type'."
        ),
        status=400,
        error_code="UNROUTABLE_PAYLOAD",
        request_id=request_id,
    )


def _route_to_state(
    req: Any,
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """Store working memory (state) via DynamoDB.

    Args:
        req: Validated UnifiedMemoryCreateRequest.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        201 Created with state data and ``memory_type = "state"``.
    """
    from lib.dynamo import put_state  # noqa: PLC0415

    session_id = req.session_id or str(uuid.uuid4())
    result = put_state(
        tenant_id=tenant_id,
        agent_id=req.agent_id,
        session_id=session_id,
        data=req.data,
        ttl_hours=req.ttl_hours,
    )
    result["memory_type"] = "state"

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": req.agent_id,
                "action": "unified_create_state",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body=result, status=201, request_id=request_id, start_time=start_time
    )


def _route_to_episodic(
    req: Any,
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """Store episodic memory via DynamoDB.

    Args:
        req: Validated UnifiedMemoryCreateRequest.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        201 Created with episode data and ``memory_type = "episodic"``.
    """
    from lib.episodes import put_episode  # noqa: PLC0415

    session_id = req.session_id or str(uuid.uuid4())
    result = put_episode(
        tenant_id=tenant_id,
        agent_id=req.agent_id,
        session_id=session_id,
        episode_type=req.type,
        content=req.content,
        metadata=req.metadata,
    )
    result["memory_type"] = "episodic"

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": req.agent_id,
                "action": "unified_create_episodic",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body=result, status=201, request_id=request_id, start_time=start_time
    )


def _route_to_semantic(
    req: Any,
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """Store semantic memory via Aurora pgvector with Bedrock embedding.

    Args:
        req: Validated UnifiedMemoryCreateRequest.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        201 Created with semantic memory data and ``memory_type = "semantic"``.
    """
    from lib.aurora import get_connection, set_tenant_context  # noqa: PLC0415
    from lib.embeddings import generate_embedding  # noqa: PLC0415

    embedding = generate_embedding(req.content)
    embedding_str = str(embedding)

    with get_connection() as conn:
        set_tenant_context(conn, tenant_id)

        # Deduplication: cosine similarity > 0.95 within same tenant/agent.
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
                    RETURNING id, agent_id, namespace, content, metadata,
                              created_at, updated_at
                    """,
                    (
                        req.content,
                        embedding_str,
                        json.dumps(merged_metadata),
                        existing["id"],
                    ),
                )
                row = cur.fetchone()
            row_data = dict(row) if row else {}
            result = _semantic_row_to_dict(row_data, deduplicated=True)
        else:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO semantic_memory
                        (tenant_id, agent_id, namespace, content,
                         embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s::vector, %s::jsonb)
                    RETURNING id, agent_id, namespace, content, metadata,
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
                row = cur.fetchone()
            row_data = dict(row) if row else {}
            result = _semantic_row_to_dict(row_data, deduplicated=False)

    result["memory_type"] = "semantic"

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": req.agent_id,
                "action": "unified_create_semantic",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body=result, status=201, request_id=request_id, start_time=start_time
    )


def _handle_get_agent(
    tenant_id: str,
    agent_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """GET /v1/memory/{agent_id} — combined view across all memory stores.

    Fetches from DynamoDB (state + episodes) and Aurora (semantic) in
    sequence. If an individual store fails, that store's data is omitted
    and a warning is appended — the overall request still succeeds with
    partial data.

    Args:
        tenant_id: Tenant identifier from the Lambda authorizer.
        agent_id: Agent identifier from the path.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with combined data across all stores plus a summary dict.
    """
    warnings: list[str] = []

    # --- Working memory: latest state (default session) ---
    state_data: dict[str, Any] | None = None
    try:
        from lib.dynamo import get_state  # noqa: PLC0415

        state_data = get_state(
            tenant_id=tenant_id, agent_id=agent_id, session_id="default"
        )
    except Exception:
        logger.exception(
            "Failed to fetch state for agent",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )
        warnings.append("Failed to retrieve working memory (state store unavailable)")

    # --- Semantic memory: top-5 most recent memories ---
    semantic_results: list[dict[str, Any]] = []
    try:
        from lib.aurora import get_connection, set_tenant_context  # noqa: PLC0415

        with get_connection() as conn:
            set_tenant_context(conn, tenant_id)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, agent_id, namespace, content, metadata,
                           created_at, updated_at
                    FROM semantic_memory
                    WHERE tenant_id = %s
                      AND agent_id = %s
                      AND NOT is_deleted
                    ORDER BY created_at DESC
                    LIMIT 5
                    """,
                    (tenant_id, agent_id),
                )
                rows = cur.fetchall()
        semantic_results = [_semantic_row_to_dict(dict(r)) for r in rows]
    except Exception:
        logger.exception(
            "Failed to fetch semantic memories for agent",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )
        warnings.append("Failed to retrieve semantic memory (Aurora store unavailable)")

    # --- Episodic memory: last 10 episodes ---
    episodic_results: list[dict[str, Any]] = []
    try:
        from lib.episodes import query_episodes  # noqa: PLC0415

        episodic_results = query_episodes(
            tenant_id=tenant_id,
            agent_id=agent_id,
            limit=10,
        )
    except Exception:
        logger.exception(
            "Failed to fetch episodes for agent",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )
        warnings.append(
            "Failed to retrieve episodic memory (DynamoDB store unavailable)"
        )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "action": "unified_get_agent",
                "semantic_count": len(semantic_results),
                "episodic_count": len(episodic_results),
                "state_found": state_data is not None,
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    response_body: dict[str, Any] = {
        "agent_id": agent_id,
        "state": state_data,
        "semantic": semantic_results,
        "episodic": episodic_results,
        "summary": {
            "state_exists": state_data is not None,
            "semantic_count": len(semantic_results),
            "episodic_count": len(episodic_results),
        },
    }
    if warnings:
        response_body["warnings"] = warnings

    return success_response(
        body=response_body,
        request_id=request_id,
        start_time=start_time,
    )


def _handle_search(
    event: dict[str, Any],
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """POST /v1/memory/search — cross-memory search.

    Searches semantic memory via vector similarity and episodic memory via
    substring match on content. Results are merged with semantic first
    (sorted by score descending) then episodic (sorted by timestamp desc).

    Request body:
        query (str)       — natural language search query
        agent_id (str)    — optional agent filter
        top_k (int)       — max results per store (default 10)
        threshold (float) — min cosine similarity for semantic (default 0.5)

    Args:
        event: API Gateway HTTP API v2 event payload.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with merged ``results`` list and ``count``.
    """
    from pydantic import ValidationError  # noqa: PLC0415

    from lib.models import UnifiedSearchRequest  # noqa: PLC0415

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
        req = UnifiedSearchRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    semantic_results: list[dict[str, Any]] = []
    episodic_results: list[dict[str, Any]] = []

    # --- Semantic search via pgvector ---
    try:
        from lib.aurora import get_connection, set_tenant_context  # noqa: PLC0415
        from lib.embeddings import generate_embedding  # noqa: PLC0415

        query_embedding = generate_embedding(req.query)
        embedding_str = str(query_embedding)

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
        params: list[Any] = [
            embedding_str,
            tenant_id,
            embedding_str,
            req.threshold,
        ]

        if req.agent_id is not None:
            query_parts.append("AND agent_id = %s")
            params.append(req.agent_id)

        query_parts.append("ORDER BY similarity DESC LIMIT %s")
        params.append(req.top_k)

        full_query = "\n".join(query_parts)

        with get_connection() as conn:
            set_tenant_context(conn, tenant_id)
            with conn.cursor() as cur:
                cur.execute(full_query, tuple(params))
                rows = cur.fetchall()

        for row in rows:
            r = _semantic_row_to_dict(
                dict(row), similarity_score=float(row["similarity"])
            )
            r["memory_type"] = "semantic"
            semantic_results.append(r)

    except Exception:
        logger.exception(
            "Semantic search failed in cross-memory search",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )

    # --- Episodic search via substring match on recent episodes ---
    try:
        from lib.episodes import query_episodes  # noqa: PLC0415

        episodes = query_episodes(
            tenant_id=tenant_id,
            agent_id=req.agent_id or "",
            limit=req.top_k * 5,  # over-fetch then filter
        )
        query_lower = req.query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 2]

        for ep in episodes:
            content = ep.get("content", "")
            if isinstance(content, str):
                content_lower = content.lower()
            else:
                content_lower = json.dumps(content).lower()

            if any(word in content_lower for word in query_words):
                ep_result = dict(ep)
                ep_result["memory_type"] = "episodic"
                ep_result["relevance"] = "text_match"
                episodic_results.append(ep_result)
                if len(episodic_results) >= req.top_k:
                    break

    except Exception:
        logger.exception(
            "Episodic search failed in cross-memory search",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )

    # Merge: semantic first (by score), then episodic (already timestamp-sorted).
    all_results = semantic_results + episodic_results

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": req.agent_id,
                "action": "unified_search",
                "semantic_count": len(semantic_results),
                "episodic_count": len(episodic_results),
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body={"results": all_results, "count": len(all_results)},
        request_id=request_id,
        start_time=start_time,
    )


def _handle_purge(
    tenant_id: str,
    agent_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """DELETE /v1/memory/{agent_id} — GDPR purge across all stores.

    Deletes all data for an agent across DynamoDB (state + episodes),
    Aurora (semantic_memory), and S3 (archived episodes).  The operation
    is idempotent — calling it twice is safe.

    Args:
        tenant_id: Tenant identifier from the Lambda authorizer.
        agent_id: Agent identifier from the path.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with counts of deleted items per store.
    """
    deleted_state = 0
    deleted_episodic = 0
    deleted_semantic = 0
    deleted_s3 = 0

    # --- Delete all DynamoDB items for this pk (state + episodes) ---
    try:
        dynamo_counts = _purge_dynamo_items(tenant_id, agent_id)
        deleted_state = dynamo_counts["state"]
        deleted_episodic = dynamo_counts["episodic"]
    except Exception:
        logger.exception(
            "DynamoDB purge failed",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )

    # --- Delete all Aurora semantic_memory rows ---
    try:
        from lib.aurora import get_connection, set_tenant_context  # noqa: PLC0415

        with get_connection() as conn:
            set_tenant_context(conn, tenant_id)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM semantic_memory
                    WHERE tenant_id = %s
                      AND agent_id = %s
                    """,
                    (tenant_id, agent_id),
                )
                deleted_semantic = cur.rowcount if cur.rowcount >= 0 else 0

    except Exception:
        logger.exception(
            "Aurora purge failed",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )

    # --- Delete S3 archived episodes under {tenant_id}/{agent_id}/ ---
    try:
        deleted_s3 = _purge_s3_objects(tenant_id, agent_id)
    except Exception:
        logger.exception(
            "S3 purge failed",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "action": "unified_purge",
                "deleted_state": deleted_state,
                "deleted_episodic": deleted_episodic,
                "deleted_semantic": deleted_semantic,
                "deleted_s3": deleted_s3,
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body={
            "agent_id": agent_id,
            "deleted": {
                "state": deleted_state,
                "semantic": deleted_semantic,
                "episodic": deleted_episodic,
                "s3_objects": deleted_s3,
            },
        },
        request_id=request_id,
        start_time=start_time,
    )


def _handle_usage(
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """GET /v1/usage — per-tenant usage stats for the current billing period.

    Fetches counters from DynamoDB usage tracking, then computes on-the-fly
    stats for agent count and semantic memory count.

    Args:
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with usage stats dict.
    """
    from lib.usage import get_usage  # noqa: PLC0415

    usage = get_usage(tenant_id)

    # --- On-the-fly stats: agent count from DynamoDB ---
    dynamo_items = 0
    agents_count = 0
    sessions_count = 0
    try:
        stats = _get_dynamo_usage_stats(tenant_id)
        dynamo_items = stats["dynamo_items"]
        agents_count = stats["agents_count"]
        sessions_count = stats["sessions_count"]
    except Exception:
        logger.exception(
            "Failed to compute DynamoDB usage stats",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )

    # --- On-the-fly stats: semantic memory count from Aurora ---
    semantic_memories = 0
    try:
        from lib.aurora import get_connection, set_tenant_context  # noqa: PLC0415

        with get_connection() as conn:
            set_tenant_context(conn, tenant_id)
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM semantic_memory
                    WHERE tenant_id = %s
                      AND NOT is_deleted
                    """,
                    (tenant_id,),
                )
                row = cur.fetchone()
                if row:
                    semantic_memories = int(row["cnt"])
    except Exception:
        logger.exception(
            "Failed to compute semantic memory count",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "action": "usage_get",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body={
            "api_calls_month": usage["api_calls"],
            "embeddings_generated_month": usage["embeddings"],
            "storage": {
                "dynamodb_items": dynamo_items,
                "semantic_memories": semantic_memories,
                "s3_objects": 0,  # not computed on-the-fly (S3 inventory needed)
            },
            "agents_count": agents_count,
            "sessions_count": sessions_count,
            "billing_period": usage["month"],
        },
        request_id=request_id,
        start_time=start_time,
    )


# ---------------------------------------------------------------------------
# Private infrastructure helpers (extracted for testability)
# ---------------------------------------------------------------------------


def _purge_dynamo_items(tenant_id: str, agent_id: str) -> dict[str, int]:
    """Delete all DynamoDB items for a tenant/agent partition.

    Queries all items where ``pk = {tenant_id}#{agent_id}`` and batch-deletes
    them.  Counts state (SESSION#) and episodic (EPISODE#) items separately.

    Args:
        tenant_id: Tenant identifier.
        agent_id: Agent identifier.

    Returns:
        Dict with ``state`` and ``episodic`` integer counts.
    """
    import boto3  # noqa: PLC0415
    import boto3.dynamodb.conditions as conditions  # noqa: PLC0415

    table_name = os.environ.get("STATE_TABLE_NAME", "mnemora-state-dev")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    pk = f"{tenant_id}#{agent_id}"
    key_condition = conditions.Key("pk").eq(pk)
    deleted_state = 0
    deleted_episodic = 0
    last_key: dict[str, Any] | None = None

    while True:
        query_kwargs: dict[str, Any] = {
            "KeyConditionExpression": key_condition,
            "ProjectionExpression": "pk, sk",
        }
        if last_key:
            query_kwargs["ExclusiveStartKey"] = last_key

        response = table.query(**query_kwargs)
        items = response.get("Items", [])

        with table.batch_writer() as batch:
            for item in items:
                batch.delete_item(Key={"pk": item["pk"], "sk": item["sk"]})
                if item["sk"].startswith("SESSION#"):
                    deleted_state += 1
                elif item["sk"].startswith("EPISODE#"):
                    deleted_episodic += 1

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

    return {"state": deleted_state, "episodic": deleted_episodic}


def _purge_s3_objects(tenant_id: str, agent_id: str) -> int:
    """Delete all S3 objects under the agent prefix.

    Paginates through ``{tenant_id}/{agent_id}/`` and batch-deletes up to
    1000 objects per S3 ``delete_objects`` call.

    Args:
        tenant_id: Tenant identifier (used as S3 key prefix).
        agent_id: Agent identifier (second path component).

    Returns:
        Total number of S3 objects deleted.
    """
    import boto3  # noqa: PLC0415

    bucket = os.environ.get("EPISODE_BUCKET", "mnemora-episodes-dev")
    prefix = f"{tenant_id}/{agent_id}/"
    s3_client = boto3.client("s3")

    paginator = s3_client.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    objects_to_delete: list[dict[str, str]] = []
    for page in pages:
        for obj in page.get("Contents", []):
            objects_to_delete.append({"Key": obj["Key"]})

    if not objects_to_delete:
        return 0

    batch_size = 1000
    for i in range(0, len(objects_to_delete), batch_size):
        batch = objects_to_delete[i : i + batch_size]
        s3_client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": batch, "Quiet": True},
        )

    return len(objects_to_delete)


def _get_dynamo_usage_stats(tenant_id: str) -> dict[str, int]:
    """Compute on-the-fly DynamoDB usage statistics for a tenant.

    Scans the state table counting total items, distinct agents (by
    SESSION# pk), and total sessions. Uses ``Select: COUNT`` for the
    total count to avoid reading item data.

    Args:
        tenant_id: Tenant identifier.

    Returns:
        Dict with ``dynamo_items``, ``agents_count``, ``sessions_count``.
    """
    import boto3  # noqa: PLC0415
    import boto3.dynamodb.conditions as conditions  # noqa: PLC0415

    table_name = os.environ.get("STATE_TABLE_NAME", "mnemora-state-dev")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    # Total item count for the tenant.
    dynamo_items = 0
    scan_kwargs: dict[str, Any] = {
        "FilterExpression": conditions.Attr("pk").begins_with(f"{tenant_id}#"),
        "Select": "COUNT",
    }
    last_key = None
    while True:
        if last_key:
            scan_kwargs["ExclusiveStartKey"] = last_key
        response = table.scan(**scan_kwargs)
        dynamo_items += response.get("Count", 0)
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break

    # Distinct agents and session count.
    agent_pks: set[str] = set()
    sessions_count = 0
    session_scan_kwargs: dict[str, Any] = {
        "FilterExpression": (
            conditions.Attr("pk").begins_with(f"{tenant_id}#")
            & conditions.Attr("sk").begins_with("SESSION#")
        ),
        "ProjectionExpression": "pk, sk",
    }
    last_key = None
    while True:
        if last_key:
            session_scan_kwargs["ExclusiveStartKey"] = last_key
        sess_response = table.scan(**session_scan_kwargs)
        for item in sess_response.get("Items", []):
            agent_pks.add(item["pk"])
            sessions_count += 1
        last_key = sess_response.get("LastEvaluatedKey")
        if not last_key:
            break

    return {
        "dynamo_items": dynamo_items,
        "agents_count": len(agent_pks),
        "sessions_count": sessions_count,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _semantic_row_to_dict(
    row: dict[str, Any],
    *,
    similarity_score: float | None = None,
    deduplicated: bool = False,
) -> dict[str, Any]:
    """Convert a ``semantic_memory`` database row dict to a response dict.

    Args:
        row: Dict returned by psycopg ``dict_row`` factory.
        similarity_score: Cosine similarity score, if from a search query.
        deduplicated: True when an existing row was updated in-place.

    Returns:
        Dict matching the SemanticResponse shape.
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
        "id": str(row.get("id", "")),
        "agent_id": row.get("agent_id", ""),
        "content": row.get("content", ""),
        "namespace": row.get("namespace", "default"),
        "metadata": row.get("metadata") or {},
        "similarity_score": similarity_score,
        "created_at": _dt_to_iso(row.get("created_at")),
        "updated_at": _dt_to_iso(row.get("updated_at")),
        "deduplicated": deduplicated,
    }
