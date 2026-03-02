"""Mnemora SDK — Python client for the Mnemora AI agent memory API.

Mnemora provides four memory types via a single REST API:

- **Working memory** (DynamoDB) — fast key-value state per agent/session
- **Semantic memory** (Aurora pgvector) — vector similarity search over text
- **Episodic memory** (DynamoDB + S3) — time-series event logs
- **Unified** — cross-memory search and GDPR purge

Quick-start (async)::

    import asyncio
    from mnemora import MnemoraClient

    async def main():
        async with MnemoraClient(api_key="mnm_...") as client:
            # Store a fact as semantic memory
            await client.store_memory("agent-1", "The user prefers concise replies.")

            # Vector search
            results = await client.search_memory("user preferences", agent_id="agent-1")

            # Track an event
            await client.store_episode(
                agent_id="agent-1",
                session_id="sess-abc",
                type="conversation",
                content={"role": "user", "message": "Hello"},
            )

    asyncio.run(main())

Quick-start (sync)::

    from mnemora import MnemoraSync

    with MnemoraSync(api_key="mnm_...") as client:
        client.store_state("agent-1", {"plan": "write a report"})
        state = client.get_state("agent-1")
        print(state.data)

Environment variables
---------------------
MNEMORA_API_URL
    Override the API base URL without touching code.
"""

from __future__ import annotations

from mnemora.client import MnemoraClient
from mnemora.exceptions import (
    MnemoraAuthError,
    MnemoraConflictError,
    MnemoraError,
    MnemoraNotFoundError,
    MnemoraRateLimitError,
    MnemoraValidationError,
)
from mnemora.models import (
    EpisodeResponse,
    PurgeResponse,
    SearchResult,
    SemanticResponse,
    StateResponse,
    UsageResponse,
)
from mnemora.sync_client import MnemoraSync

__version__ = "0.1.0"

__all__ = [
    # Clients
    "MnemoraClient",
    "MnemoraSync",
    # Exceptions
    "MnemoraError",
    "MnemoraAuthError",
    "MnemoraNotFoundError",
    "MnemoraConflictError",
    "MnemoraRateLimitError",
    "MnemoraValidationError",
    # Models
    "StateResponse",
    "SemanticResponse",
    "EpisodeResponse",
    "SearchResult",
    "PurgeResponse",
    "UsageResponse",
    # Version
    "__version__",
]
