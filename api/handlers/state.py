"""Working memory handler — full CRUD for agent state via DynamoDB.

Routes:
    POST   /v1/state                          — create state
    GET    /v1/state/{agent_id}               — get current state (default session)
    GET    /v1/state/{agent_id}/sessions      — list all sessions
    PUT    /v1/state/{agent_id}               — update with optimistic locking
    DELETE /v1/state/{agent_id}/{session_id}  — delete a specific session

All requests are dispatched from a single Lambda triggered by the
API Gateway ``{proxy+}`` catch-all route under ``/v1/state``.
Routing is done by parsing the path from the event's requestContext.
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

# DynamoDB item size cap: 400 KB
_MAX_PAYLOAD_BYTES = 400 * 1024


class _PayloadTooLargeError(Exception):
    """Raised when the request body exceeds the DynamoDB item size limit."""


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """Handle working memory state requests.

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
                "handler": "state",
            }
        )
    )

    try:
        segments = _parse_path_segments(path)

        if method == "POST" and len(segments) == 0:
            return _handle_create(event, tenant_id, request_id, start_time)

        if method == "GET" and len(segments) == 1:
            return _handle_get(event, tenant_id, segments[0], request_id, start_time)

        if method == "GET" and len(segments) == 2 and segments[1] == "sessions":
            return _handle_list_sessions(tenant_id, segments[0], request_id, start_time)

        if method == "PUT" and len(segments) == 1:
            return _handle_update(event, tenant_id, segments[0], request_id, start_time)

        if method == "DELETE" and len(segments) == 2:
            return _handle_delete(
                tenant_id, segments[0], segments[1], request_id, start_time
            )

        return error_response(
            message=f"Not found: {method} {path}",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    except Exception:
        logger.exception(
            "Unhandled error in state handler",
            extra={"request_id": request_id, "tenant_id": tenant_id},
        )
        return error_response(
            message="Internal server error",
            status=500,
            error_code="INTERNAL_ERROR",
            request_id=request_id,
        )


# ---------------------------------------------------------------------------
# Path parsing
# ---------------------------------------------------------------------------


def _extract_request_id(event: dict[str, Any]) -> str:
    """Extract request_id from API Gateway event context.

    Args:
        event: API Gateway HTTP API v2 event payload.

    Returns:
        The requestId string, or 'unknown' if absent.
    """
    return event.get("requestContext", {}).get("requestId", "unknown")


def _parse_path_segments(path: str) -> list[str]:
    """Return the path segments that follow ``/v1/state``.

    Args:
        path: Full request path from requestContext.http.path.

    Returns:
        List of non-empty path segments after the ``/v1/state`` prefix.

    Examples::

        _parse_path_segments("/v1/state")           # []
        _parse_path_segments("/v1/state/agent-1")   # ["agent-1"]
        _parse_path_segments("/v1/state/a/sessions")# ["a", "sessions"]
        _parse_path_segments("/v1/state/a/sess-1")  # ["a", "sess-1"]
    """
    prefix = "/v1/state"
    remainder = path[len(prefix) :] if path.startswith(prefix) else path
    return [s for s in remainder.split("/") if s]


# ---------------------------------------------------------------------------
# Body parsing
# ---------------------------------------------------------------------------


def _parse_body(event: dict[str, Any]) -> dict[str, Any]:
    """Decode and size-check the JSON request body.

    Args:
        event: API Gateway HTTP API v2 event payload.

    Returns:
        Parsed body dict. Empty dict when there is no body.

    Raises:
        _PayloadTooLargeError: Body exceeds _MAX_PAYLOAD_BYTES.
        json.JSONDecodeError: Body is not valid JSON.
        TypeError: Body is not a string.
    """
    body_str = event.get("body") or ""

    if len(body_str.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
        raise _PayloadTooLargeError(
            f"Request body exceeds {_MAX_PAYLOAD_BYTES // 1024}KB limit"
        )

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
    """POST /v1/state — create a new agent state item."""
    from pydantic import ValidationError

    from lib.dynamo import put_state
    from lib.models import StateCreateRequest

    try:
        body = _parse_body(event)
    except _PayloadTooLargeError as exc:
        return error_response(
            message=str(exc),
            status=413,
            error_code="PAYLOAD_TOO_LARGE",
            request_id=request_id,
        )
    except (json.JSONDecodeError, TypeError):
        return error_response(
            message="Invalid JSON in request body",
            status=400,
            error_code="INVALID_JSON",
            request_id=request_id,
        )

    try:
        req = StateCreateRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    result = put_state(
        tenant_id=tenant_id,
        agent_id=req.agent_id,
        session_id=req.session_id,
        data=req.data,
        ttl_hours=req.ttl_hours,
    )

    return success_response(
        body=result, status=201, request_id=request_id, start_time=start_time
    )


def _handle_get(
    event: dict[str, Any],
    tenant_id: str,
    agent_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """GET /v1/state/{agent_id}?session_id=<id> — fetch session state.

    If the ``session_id`` query parameter is omitted the handler defaults
    to ``"default"``.
    """
    from lib.dynamo import get_state

    query_params = event.get("queryStringParameters") or {}
    session_id = query_params.get("session_id", "default")

    result = get_state(tenant_id=tenant_id, agent_id=agent_id, session_id=session_id)

    if result is None:
        return error_response(
            message=f"No state found for agent '{agent_id}' session '{session_id}'",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    return success_response(body=result, request_id=request_id, start_time=start_time)


def _handle_list_sessions(
    tenant_id: str,
    agent_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """GET /v1/state/{agent_id}/sessions — list all sessions for an agent."""
    from lib.dynamo import list_sessions

    sessions = list_sessions(tenant_id=tenant_id, agent_id=agent_id)

    return success_response(
        body={"agent_id": agent_id, "sessions": sessions, "count": len(sessions)},
        request_id=request_id,
        start_time=start_time,
    )


def _handle_update(
    event: dict[str, Any],
    tenant_id: str,
    agent_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """PUT /v1/state/{agent_id} — update state with optimistic locking."""
    from pydantic import ValidationError

    from lib.dynamo import update_state
    from lib.models import StateUpdateRequest

    try:
        body = _parse_body(event)
    except _PayloadTooLargeError as exc:
        return error_response(
            message=str(exc),
            status=413,
            error_code="PAYLOAD_TOO_LARGE",
            request_id=request_id,
        )
    except (json.JSONDecodeError, TypeError):
        return error_response(
            message="Invalid JSON in request body",
            status=400,
            error_code="INVALID_JSON",
            request_id=request_id,
        )

    try:
        req = StateUpdateRequest(**body)
    except ValidationError as exc:
        return error_response(
            message=str(exc),
            status=400,
            error_code="VALIDATION_ERROR",
            request_id=request_id,
        )

    try:
        result = update_state(
            tenant_id=tenant_id,
            agent_id=agent_id,
            session_id=req.session_id,
            data=req.data,
            expected_version=req.version,
            ttl_hours=req.ttl_hours,
        )
    except Exception as exc:
        # Duck-type check for botocore ClientError without importing botocore
        # at module level (avoids hard dependency in test environments).
        error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
        if error_code == "ConditionalCheckFailedException":
            return error_response(
                message="Version conflict — state was modified by another request",
                status=409,
                error_code="VERSION_CONFLICT",
                request_id=request_id,
            )
        raise

    return success_response(body=result, request_id=request_id, start_time=start_time)


def _handle_delete(
    tenant_id: str,
    agent_id: str,
    session_id: str,
    request_id: str,
    start_time: float,
) -> dict[str, Any]:
    """DELETE /v1/state/{agent_id}/{session_id} — remove a specific session."""
    from lib.dynamo import delete_state

    deleted = delete_state(
        tenant_id=tenant_id, agent_id=agent_id, session_id=session_id
    )

    if not deleted:
        return error_response(
            message=f"Session '{session_id}' not found for agent '{agent_id}'",
            status=404,
            error_code="NOT_FOUND",
            request_id=request_id,
        )

    return success_response(
        body={"deleted": True, "agent_id": agent_id, "session_id": session_id},
        request_id=request_id,
        start_time=start_time,
    )
