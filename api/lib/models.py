"""Pydantic v2 models for Mnemora API request/response validation."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Semantic memory models
# ---------------------------------------------------------------------------


class SemanticCreateRequest(BaseModel):
    """Request body for POST /v1/memory/semantic."""

    agent_id: str = Field(
        ..., min_length=1, max_length=256, description="Agent identifier"
    )
    content: str = Field(
        ..., min_length=1, description="Text content to embed and store"
    )
    namespace: str = Field(
        default="default",
        min_length=1,
        max_length=128,
        description="Logical namespace for grouping memories",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary JSON metadata attached to the memory",
    )


class SemanticSearchRequest(BaseModel):
    """Request body for POST /v1/memory/semantic/search."""

    query: str = Field(
        ..., min_length=1, description="Natural language query to search for"
    )
    agent_id: Optional[str] = Field(
        default=None, description="Restrict search to a specific agent"
    )
    namespace: Optional[str] = Field(
        default=None, description="Restrict search to a specific namespace"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to return",
    )
    threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score (0.0–1.0)",
    )
    metadata_filter: Optional[dict[str, Any]] = Field(
        default=None,
        description="JSONB containment filter applied to metadata column",
    )


class SemanticResponse(BaseModel):
    """Response body for semantic memory operations."""

    id: str
    agent_id: str
    content: str
    namespace: str
    metadata: dict[str, Any]
    similarity_score: Optional[float] = None
    created_at: str
    updated_at: str
    deduplicated: bool = False


# ---------------------------------------------------------------------------
# Working memory (state) models
# ---------------------------------------------------------------------------


class StateCreateRequest(BaseModel):
    """Request body for POST /v1/state."""

    agent_id: str = Field(
        ..., min_length=1, max_length=256, description="Agent identifier"
    )
    session_id: str = Field(
        default="default",
        min_length=1,
        max_length=256,
    )
    data: dict[str, Any] = Field(..., description="State data (JSON object, max 400KB)")
    ttl_hours: Optional[int] = Field(
        default=None,
        ge=1,
        le=8760,
        description="TTL in hours (default: 24, max: 8760 = 1 year)",
    )

    @field_validator("agent_id", "session_id")
    @classmethod
    def no_hash_in_ids(cls, v: str) -> str:
        """Reject IDs containing '#' which would corrupt DynamoDB key structure."""
        if "#" in v:
            raise ValueError("ID must not contain '#' character")
        return v


class StateUpdateRequest(BaseModel):
    """Request body for PUT /v1/state/{agent_id}."""

    session_id: str = Field(default="default", min_length=1, max_length=256)
    data: dict[str, Any] = Field(..., description="Updated state data")
    version: int = Field(
        ..., ge=1, description="Current version for optimistic locking"
    )
    ttl_hours: Optional[int] = Field(default=None, ge=1, le=8760)

    @field_validator("session_id")
    @classmethod
    def no_hash_in_session_id(cls, v: str) -> str:
        """Reject session_id containing '#' which would corrupt DynamoDB key structure."""
        if "#" in v:
            raise ValueError("session_id must not contain '#' character")
        return v


class StateResponse(BaseModel):
    """Response body for state operations."""

    agent_id: str
    session_id: str
    data: dict[str, Any]
    version: int
    created_at: str
    updated_at: str
    expires_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Episodic memory models
# ---------------------------------------------------------------------------

_ALLOWED_EPISODE_TYPES = {"conversation", "action", "observation", "tool_call"}


class EpisodeCreateRequest(BaseModel):
    """Request body for POST /v1/memory/episodic."""

    agent_id: str = Field(
        ..., min_length=1, max_length=256, description="Agent identifier"
    )
    session_id: str = Field(
        ..., min_length=1, max_length=256, description="Session identifier"
    )
    type: str = Field(..., description="Episode type")
    content: Any = Field(..., description="Episode content (string or dict)")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata"
    )

    @field_validator("agent_id", "session_id")
    @classmethod
    def no_hash_in_ids(cls, v: str) -> str:
        """Reject IDs containing '#' which would corrupt DynamoDB key structure."""
        if "#" in v:
            raise ValueError("ID must not contain '#' character")
        return v

    @field_validator("type")
    @classmethod
    def valid_type(cls, v: str) -> str:
        """Validate that the episode type is one of the allowed values."""
        if v not in _ALLOWED_EPISODE_TYPES:
            raise ValueError(
                f"type must be one of: {', '.join(sorted(_ALLOWED_EPISODE_TYPES))}"
            )
        return v


class EpisodeResponse(BaseModel):
    """Response body for episodic memory operations."""

    id: str
    agent_id: str
    session_id: str
    type: str
    content: Any
    metadata: dict[str, Any]
    timestamp: str


class EpisodeSummaryRequest(BaseModel):
    """Request body for POST /v1/memory/episodic/{agent_id}/summarize."""

    num_episodes: int = Field(
        default=50, ge=1, le=500, description="Number of recent episodes to summarize"
    )
    target_length: int = Field(
        default=500,
        ge=50,
        le=5000,
        description="Target summary length in words",
    )


# ---------------------------------------------------------------------------
# Unified memory models
# ---------------------------------------------------------------------------


class UnifiedMemoryCreateRequest(BaseModel):
    """Request body for POST /v1/memory — auto-routing across memory types.

    Routing rules (evaluated in order):
    - ``data`` (dict) + ``session_id`` (str)  → working memory (state)
    - ``content`` (str) + ``type`` in allowed episode types → episodic memory
    - ``content`` (str) without ``type`` → semantic memory
    """

    agent_id: str = Field(
        ..., min_length=1, max_length=256, description="Agent identifier"
    )
    # Working memory fields
    session_id: Optional[str] = Field(
        default=None, min_length=1, max_length=256, description="Session identifier"
    )
    data: Optional[dict[str, Any]] = Field(
        default=None, description="State data for working memory"
    )
    # Semantic / episodic fields
    content: Optional[Any] = Field(
        default=None, description="Content for semantic (str) or episodic (str or dict)"
    )
    type: Optional[str] = Field(
        default=None,
        description="Episode type (conversation, action, observation, tool_call)",
    )
    # Shared optional fields
    namespace: str = Field(
        default="default",
        min_length=1,
        max_length=128,
        description="Namespace for semantic memory",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Optional metadata"
    )
    ttl_hours: Optional[int] = Field(
        default=None, ge=1, le=8760, description="TTL in hours (working memory only)"
    )

    @field_validator("agent_id", "session_id")
    @classmethod
    def no_hash_in_ids(cls, v: Optional[str]) -> Optional[str]:
        """Reject IDs containing '#' which would corrupt DynamoDB key structure."""
        if v is not None and "#" in v:
            raise ValueError("ID must not contain '#' character")
        return v


class UnifiedSearchRequest(BaseModel):
    """Request body for POST /v1/memory/search — cross-memory search."""

    query: str = Field(..., min_length=1, description="Natural language search query")
    agent_id: Optional[str] = Field(
        default=None, description="Restrict search to a specific agent"
    )
    top_k: int = Field(
        default=10, ge=1, le=100, description="Maximum number of results to return"
    )
    threshold: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity for semantic results",
    )
