"""Pydantic v2 response models for the Mnemora API.

All models accept extra fields so that the SDK remains forward-compatible
when the API adds new response attributes. Unknown fields are silently
ignored — existing attributes are never removed from a model without a
major-version bump.

Example::

    from mnemora.models import StateResponse, SemanticResponse

    state: StateResponse = await client.get_state("agent-1")
    print(state.data)         # dict with arbitrary keys
    print(state.version)      # optimistic-lock version counter
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class _BaseResponse(BaseModel):
    """Shared configuration for all response models."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class StateResponse(_BaseResponse):
    """Working-memory (DynamoDB) state record.

    Attributes:
        agent_id: Identifier of the owning agent.
        session_id: Session within the agent (default "default").
        data: Arbitrary key-value payload stored by the agent.
        version: Monotonically increasing integer used for optimistic locking.
            Pass this back to update_state() to prevent lost updates.
        created_at: ISO 8601 timestamp of record creation.
        updated_at: ISO 8601 timestamp of last update.
        expires_at: ISO 8601 timestamp after which DynamoDB will delete the
            record, or None if the record has no TTL.
    """

    agent_id: str
    session_id: str
    data: dict[str, Any]
    version: int
    created_at: str
    updated_at: str
    expires_at: str | None = None


class SemanticResponse(_BaseResponse):
    """Semantic-memory record stored in Aurora pgvector.

    Attributes:
        id: UUID of the memory item.
        agent_id: Identifier of the owning agent.
        content: The raw text content that was embedded and stored.
        namespace: Logical partition within an agent (default "default").
        metadata: Arbitrary JSON metadata attached at store time.
        similarity_score: Cosine similarity score [0, 1] — only present in
            search results, None for direct-GET responses.
        created_at: ISO 8601 timestamp of creation.
        updated_at: ISO 8601 timestamp of last update.
        deduplicated: True when the server merged this payload into an
            existing record instead of inserting a new one.
    """

    id: str
    agent_id: str
    content: str
    namespace: str
    metadata: dict[str, Any] = {}
    similarity_score: float | None = None
    created_at: str
    updated_at: str
    deduplicated: bool = False


class EpisodeResponse(_BaseResponse):
    """Episodic-memory record (DynamoDB hot-tier / S3 cold-tier).

    Attributes:
        id: Unique identifier for the episode.
        agent_id: Identifier of the owning agent.
        session_id: Session that produced the episode.
        type: Event classification — one of "conversation", "action",
            "observation", or "tool_call".
        content: Raw episode payload (text or structured object).
        metadata: Arbitrary JSON metadata.
        timestamp: ISO 8601 timestamp when the episode occurred.
    """

    id: str
    agent_id: str
    session_id: str
    type: str
    content: Any
    metadata: dict[str, Any] = {}
    timestamp: str


class SearchResult(_BaseResponse):
    """A single result from a cross-memory search (POST /v1/memory/search).

    Attributes:
        memory_type: Which memory tier produced this result — "semantic" or
            "episodic".
        id: Record identifier (UUID for semantic, episode ID for episodic).
        agent_id: Identifier of the owning agent.
        content: Raw record content.
        similarity_score: Vector cosine similarity [0, 1] for semantic hits.
        relevance: Text relevance label for episodic hits (e.g. "text_match").
        metadata: Record metadata.
        created_at: Creation timestamp (semantic records).
        timestamp: Episode timestamp (episodic records).
    """

    memory_type: str
    id: str | None = None
    agent_id: str | None = None
    content: Any = None
    similarity_score: float | None = None
    relevance: str | None = None
    metadata: dict[str, Any] = {}
    created_at: str | None = None
    timestamp: str | None = None


class PurgeResponse(_BaseResponse):
    """Response from DELETE /v1/memory/{agent_id} (GDPR purge).

    Attributes:
        agent_id: The agent whose data was purged.
        deleted: Record counts by tier, e.g.
            ``{"state": 2, "semantic": 45, "episodic": 120, "s3_objects": 3}``.
    """

    agent_id: str
    deleted: dict[str, int]


class UsageResponse(_BaseResponse):
    """Current billing-period usage metrics.

    Attributes:
        api_calls_month: Total API calls in the current calendar month.
        embeddings_generated_month: Total Bedrock Titan embed calls this month.
        storage: Storage byte counts keyed by tier
            (e.g. ``{"dynamo_bytes": N, "s3_bytes": N}``).
        agents_count: Number of distinct agent IDs with stored data.
        sessions_count: Number of distinct session IDs with stored data.
        billing_period: Human-readable label, e.g. "2026-03".
    """

    api_calls_month: int = 0
    embeddings_generated_month: int = 0
    storage: dict[str, int] = {}
    agents_count: int = 0
    sessions_count: int = 0
    billing_period: str = ""
