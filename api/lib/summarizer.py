"""Episode summarization via Bedrock Claude Haiku + Aurora semantic memory.

This module fetches the most recent N episodes for an agent, formats them
into a text block, calls Bedrock Claude Haiku (claude-3-haiku-20240307-v1:0)
to generate a coherent narrative summary, then stores that summary as a
semantic memory record via Aurora pgvector.

The Bedrock client is cached at module level so warm Lambda invocations
reuse an existing connection.

Usage::

    from lib.summarizer import summarize_episodes

    result = summarize_episodes(
        tenant_id="t-123",
        agent_id="my-agent",
        num_episodes=50,
        target_length=500,
    )
    # {"summary": "...", "episode_count": 42, "semantic_memory_id": "uuid", ...}
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_HAIKU_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"

# ---------------------------------------------------------------------------
# Module-level Bedrock client cache.
# ---------------------------------------------------------------------------

_bedrock_client: Any | None = None


def _get_bedrock_client() -> Any:
    """Lazily initialise and return the Bedrock Runtime client.

    Returns:
        A boto3 ``bedrock-runtime`` client instance, cached at module level.
    """
    global _bedrock_client
    if _bedrock_client is None:
        import boto3  # noqa: PLC0415

        _bedrock_client = boto3.client("bedrock-runtime")
        logger.info("Bedrock Runtime client initialised (summarizer)")
    return _bedrock_client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _format_episodes_for_prompt(episodes: list[dict[str, Any]]) -> str:
    """Format a list of episode dicts into a plain-text block for the LLM.

    Each episode is rendered as a numbered entry with its timestamp, type,
    and content.  Content is JSON-serialised when it is not a plain string.

    Args:
        episodes: List of episode response dicts (from
            :func:`~lib.episodes.get_recent_episodes`).

    Returns:
        Multi-line text block describing the episodes.
    """
    lines: list[str] = []
    for idx, ep in enumerate(episodes, start=1):
        content = ep.get("content")
        if not isinstance(content, str):
            content = json.dumps(content)
        lines.append(
            f"{idx}. [{ep.get('timestamp', '')}] ({ep.get('type', 'unknown')}): "
            f"{content}"
        )
    return "\n".join(lines)


def _call_haiku(prompt: str) -> str:
    """Invoke Bedrock Claude Haiku and return the generated text.

    Args:
        prompt: The user-role message to send to the model.

    Returns:
        The text content of the first response block.

    Raises:
        Exception: Any Bedrock API error is re-raised to the caller.
    """
    client = _get_bedrock_client()
    response = client.invoke_model(
        modelId=_HAIKU_MODEL_ID,
        body=json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            }
        ),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]


def _store_semantic_memory(
    tenant_id: str,
    agent_id: str,
    summary_text: str,
    embedding: list[float],
    extra_metadata: dict[str, Any],
) -> str:
    """Insert a summary as a semantic memory row and return its UUID.

    Args:
        tenant_id: Tenant identifier.
        agent_id: Agent identifier.
        summary_text: The generated summary text.
        embedding: 1024-dimensional float vector for the summary.
        extra_metadata: Metadata dict to store alongside the row.

    Returns:
        String UUID of the newly created semantic memory record.
    """
    from lib.aurora import get_connection, set_tenant_context  # noqa: PLC0415

    with get_connection() as conn:
        set_tenant_context(conn, tenant_id)
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO semantic_memory
                    (tenant_id, agent_id, namespace, content,
                     embedding, metadata)
                VALUES (%s, %s, %s, %s, %s::vector, %s::jsonb)
                RETURNING id
                """,
                (
                    tenant_id,
                    agent_id,
                    "episodic_summaries",
                    summary_text,
                    str(embedding),
                    json.dumps(extra_metadata),
                ),
            )
            row = cur.fetchone()

    if row is None:
        return str(uuid.uuid4())
    return str(row["id"])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def summarize_episodes(
    tenant_id: str,
    agent_id: str,
    num_episodes: int = 50,
    target_length: int = 500,
) -> dict[str, Any]:
    """Summarize recent episodes and store the result as semantic memory.

    Steps:
        1. Fetch the last ``num_episodes`` episodes via
           :func:`~lib.episodes.get_recent_episodes`.
        2. Format episodes into a structured text block.
        3. Call Bedrock Claude Haiku to generate a ~``target_length``-word
           narrative summary.
        4. Generate an embedding for the summary text.
        5. Store the summary in Aurora ``semantic_memory``.
        6. Return a result dict.

    Args:
        tenant_id: Tenant identifier derived from the API key authorizer.
        agent_id: Agent identifier.
        num_episodes: Number of most-recent episodes to include (default 50).
        target_length: Target word count for the summary (default 500).

    Returns:
        Dict with keys:
            - ``summary``: The generated narrative text.
            - ``episode_count``: Number of episodes that were summarised.
            - ``semantic_memory_id``: UUID of the stored semantic memory row.
            - ``time_range``: ``{"from": str, "to": str}`` spanning the
              episodes, or ``None`` when there are no episodes.

    Raises:
        Exception: Any Bedrock or Aurora error is propagated to the caller
            so the handler can map it to an appropriate HTTP response.
    """
    from lib.embeddings import generate_embedding  # noqa: PLC0415
    from lib.episodes import get_recent_episodes  # noqa: PLC0415

    episodes = get_recent_episodes(
        tenant_id=tenant_id,
        agent_id=agent_id,
        limit=num_episodes,
    )

    episode_count = len(episodes)

    # Determine time range from the fetched episodes.
    time_range: dict[str, str] | None = None
    if episodes:
        timestamps = [ep.get("timestamp", "") for ep in episodes if ep.get("timestamp")]
        if timestamps:
            time_range = {"from": min(timestamps), "to": max(timestamps)}

    if episode_count == 0:
        logger.info(
            json.dumps(
                {
                    "action": "summarize_no_episodes",
                    "tenant_id": tenant_id,
                    "agent_id": agent_id,
                }
            )
        )
        return {
            "summary": "",
            "episode_count": 0,
            "semantic_memory_id": None,
            "time_range": None,
        }

    episode_text = _format_episodes_for_prompt(episodes)

    prompt = (
        f"Summarize these agent episodes into a coherent narrative of approximately "
        f"{target_length} words. Focus on key decisions, actions, outcomes, and "
        f"learned patterns.\n\nEpisodes:\n{episode_text}"
    )

    summary_text = _call_haiku(prompt)

    embedding = generate_embedding(summary_text)

    extra_metadata: dict[str, Any] = {
        "source": "episodic_summary",
        "episode_count": episode_count,
        "time_range": time_range,
    }

    memory_id = _store_semantic_memory(
        tenant_id=tenant_id,
        agent_id=agent_id,
        summary_text=summary_text,
        embedding=embedding,
        extra_metadata=extra_metadata,
    )

    logger.info(
        json.dumps(
            {
                "action": "summarize_complete",
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "episode_count": episode_count,
                "semantic_memory_id": memory_id,
            }
        )
    )

    return {
        "summary": summary_text,
        "episode_count": episode_count,
        "semantic_memory_id": memory_id,
        "time_range": time_range,
    }
