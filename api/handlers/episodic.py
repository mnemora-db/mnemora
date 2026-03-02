"""Episodic memory handler — time-series episode storage and retrieval.

Routes:
    POST   /v1/memory/episodic                                — store episode
    GET    /v1/memory/episodic/{agent_id}                     — query episodes
    GET    /v1/memory/episodic/{agent_id}/sessions/{session_id} — session replay
    POST   /v1/memory/episodic/{agent_id}/summarize           — summarize to semantic

All requests are dispatched from a single Lambda triggered by the
API Gateway ``{proxy+}`` catch-all route under ``/v1/memory/episodic``.
Routing is done by inspecting the HTTP method and the path segments that
follow the ``/v1/memory/episodic`` prefix.

Tenant isolation:
    ``tenant_id`` is ALWAYS derived from the Lambda authorizer context
    (``event["requestContext"]["authorizer"]["lambda"]["tenantId"]``).
    Client-supplied tenant values are never trusted.

Storage:
    Episodes are written to DynamoDB (hot, 48-hour TTL) keyed on
    ``PK = {tenant_id}#{agent_id}`` / ``SK = EPISODE#{timestamp}#{id}``.
    A GSI (``session-index``) enables efficient per-session queries.
    Long-term archival to S3 is available via the episodes library.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

from lib.responses import error_response, success_response

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Public handler entrypoint
# ---------------------------------------------------------------------------


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle episodic memory requests.

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
                "handler": "episodic",
            }
        )
    )

    try:
        # Drop the leading ["v1", "memory", "episodic"] prefix.
        full_segments = [s for s in path.strip("/").split("/") if s]
        segments = full_segments[3:]

        # POST /v1/memory/episodic
        if method == "POST" and len(segments) == 0:
            return _handle_create(event, tenant_id, request_id, start_time)

        # POST /v1/memory/episodic/{agent_id}/summarize
        if method == "POST" and len(segments) == 2 and segments[1] == "summarize":
            return _handle_summarize(
                event, tenant_id, segments[0], request_id, start_time
            )

        # GET /v1/memory/episodic/{agent_id}
        if method == "GET" and len(segments) == 1:
            return _handle_query(event, tenant_id, segments[0], request_id, start_time)

        # GET /v1/memory/episodic/{agent_id}/sessions/{session_id}
        if method == "GET" and len(segments) == 3 and segments[1] == "sessions":
            return _handle_session_replay(
                tenant_id, segments[0], segments[2], request_id, start_time
            )

        return error_response(
            message=f"Not found: {method} {path}",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    except Exception:
        logger.exception(
            "Unhandled error in episodic handler",
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


# ---------------------------------------------------------------------------
# Route handlers
# ---------------------------------------------------------------------------


def _handle_create(
    event: dict[str, Any],
    tenant_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """POST /v1/memory/episodic — store a new episode.

    Args:
        event: API Gateway HTTP API v2 event payload.
        tenant_id: Tenant identifier from the Lambda authorizer.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        201 Created with :class:`~lib.models.EpisodeResponse`.
    """
    from pydantic import ValidationError  # noqa: PLC0415

    from lib.episodes import put_episode  # noqa: PLC0415
    from lib.models import EpisodeCreateRequest  # noqa: PLC0415

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
        req = EpisodeCreateRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    result = put_episode(
        tenant_id=tenant_id,
        agent_id=req.agent_id,
        session_id=req.session_id,
        episode_type=req.type,
        content=req.content,
        metadata=req.metadata,
    )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": req.agent_id,
                "action": "episode_created",
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body=result, status=201, request_id=request_id, start_time=start_time
    )


def _handle_query(
    event: dict[str, Any],
    tenant_id: str,
    agent_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """GET /v1/memory/episodic/{agent_id} — query episodes with optional filters.

    Supported query parameters:
        - ``from``: ISO 8601 lower bound timestamp (inclusive).
        - ``to``: ISO 8601 upper bound timestamp (inclusive).
        - ``type``: Filter by episode type.
        - ``session_id``: Restrict to a specific session (uses GSI).
        - ``limit``: Maximum number of results (default 50, max 500).

    Args:
        event: API Gateway HTTP API v2 event payload.
        tenant_id: Tenant identifier from the Lambda authorizer.
        agent_id: Agent identifier from the path.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with ``{"episodes": [...], "count": N}``.
    """
    from lib.episodes import query_episodes  # noqa: PLC0415

    query_params = event.get("queryStringParameters") or {}
    from_time: str | None = query_params.get("from")
    to_time: str | None = query_params.get("to")
    episode_type: str | None = query_params.get("type")
    session_id: str | None = query_params.get("session_id")

    raw_limit = query_params.get("limit", "50")
    try:
        limit = max(1, min(500, int(raw_limit)))
    except (ValueError, TypeError):
        limit = 50

    episodes = query_episodes(
        tenant_id=tenant_id,
        agent_id=agent_id,
        from_time=from_time,
        to_time=to_time,
        episode_type=episode_type,
        session_id=session_id,
        limit=limit,
    )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "action": "episode_query",
                "result_count": len(episodes),
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body={"episodes": episodes, "count": len(episodes)},
        request_id=request_id,
        start_time=start_time,
    )


def _handle_session_replay(
    tenant_id: str,
    agent_id: str,
    session_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """GET /v1/memory/episodic/{agent_id}/sessions/{session_id} — session replay.

    Returns every episode for the given session in chronological order,
    enabling the caller to replay the full interaction sequence.

    Args:
        tenant_id: Tenant identifier from the Lambda authorizer.
        agent_id: Agent identifier from the path.
        session_id: Session identifier from the path.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with ``{"session_id": ..., "episodes": [...], "count": N}``.
    """
    from lib.episodes import get_session_episodes  # noqa: PLC0415

    episodes = get_session_episodes(
        tenant_id=tenant_id,
        agent_id=agent_id,
        session_id=session_id,
    )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "action": "episode_session_replay",
                "result_count": len(episodes),
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body={
            "session_id": session_id,
            "episodes": episodes,
            "count": len(episodes),
        },
        request_id=request_id,
        start_time=start_time,
    )


def _handle_summarize(
    event: dict[str, Any],
    tenant_id: str,
    agent_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """POST /v1/memory/episodic/{agent_id}/summarize — summarize to semantic memory.

    Fetches recent episodes, calls Bedrock Claude Haiku to generate a
    narrative summary, then stores that summary as a semantic memory record
    in Aurora pgvector.

    Args:
        event: API Gateway HTTP API v2 event payload.
        tenant_id: Tenant identifier from the Lambda authorizer.
        agent_id: Agent identifier from the path.
        request_id: Unique request identifier for tracing.
        start_time: Unix timestamp of request arrival.

    Returns:
        200 with summarization result including ``semantic_memory_id``.
    """
    from pydantic import ValidationError  # noqa: PLC0415

    from lib.models import EpisodeSummaryRequest  # noqa: PLC0415
    from lib.summarizer import summarize_episodes  # noqa: PLC0415

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
        req = EpisodeSummaryRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    result = summarize_episodes(
        tenant_id=tenant_id,
        agent_id=agent_id,
        num_episodes=req.num_episodes,
        target_length=req.target_length,
    )

    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "action": "episode_summarize",
                "episode_count": result.get("episode_count", 0),
                "latency_ms": round((time.time() - start_time) * 1000),
            }
        )
    )

    return success_response(
        body=result,
        request_id=request_id,
        start_time=start_time,
    )
