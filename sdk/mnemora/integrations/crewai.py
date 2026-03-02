"""CrewAI storage backend backed by Mnemora working memory.

Maps CrewAI's generic key-value ``Storage`` interface to Mnemora's state API.
Each storage *key* becomes a Mnemora ``session_id`` under a fixed ``agent_id``,
keeping all CrewAI storage data logically grouped and separately retrievable
from other agent memory on the same account.

Usage::

    from mnemora import MnemoraSync
    from mnemora.integrations.crewai import MnemoraCrewStorage

    client = MnemoraSync(api_key="mnm_...")
    storage = MnemoraCrewStorage(client=client, agent_id="crew-agent")

    storage.save("plan", {"steps": ["research", "write", "review"]})
    plan = storage.load("plan")
    storage.delete("plan")

Requirements
------------
Install the ``crewai`` extra to enable CrewAI-native base-class inheritance::

    pip install "mnemora[crewai]"

The module can be *imported* without ``crewai`` installed, and
``MnemoraCrewStorage`` behaves as a plain Python class that satisfies the
same duck-typed interface expected by CrewAI.
"""

from __future__ import annotations

import contextlib
from typing import Any

try:
    from crewai.memory.storage.base import Storage

    _HAS_CREWAI = True
except ImportError:
    try:
        # Older crewai package layout
        from crewai.memory.storage import Storage  # type: ignore[no-redef]

        _HAS_CREWAI = True
    except ImportError:
        _HAS_CREWAI = False
        Storage = object  # type: ignore[assignment,misc]


class MnemoraCrewStorage(Storage):  # type: ignore[misc]
    """CrewAI storage backend that persists data in Mnemora working memory.

    Each key in the CrewAI storage maps to a ``session_id`` under a
    shared ``agent_id``.  Values are stored as the Mnemora state ``data``
    dict.  Scalar values are wrapped in ``{"value": ...}`` to satisfy the
    state API's requirement for a dict payload.

    Because CrewAI is synchronous by design, this class only accepts a
    ``MnemoraSync`` client.

    Parameters
    ----------
    client:
        A ``MnemoraSync`` instance.  The class calls synchronous methods
        directly; do not pass an async ``MnemoraClient`` here.
    agent_id:
        Mnemora agent identifier used as the namespace for all keys stored
        by this storage instance.  Defaults to ``"crewai"``.
    """

    def __init__(self, client: Any, agent_id: str = "crewai") -> None:
        self.client = client
        self.agent_id = agent_id

    # ------------------------------------------------------------------
    # Storage interface
    # ------------------------------------------------------------------

    def save(self, key: str, value: Any) -> None:
        """Persist *value* under *key*.

        Creates a new state record when the key does not exist; updates the
        existing record with optimistic locking when it does.

        Args:
            key: Storage key (mapped to a Mnemora ``session_id``).
            value: Value to store.  Must be JSON-serialisable.  Dicts are
                stored directly; all other types are wrapped as
                ``{"value": <value>}``.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        data: dict[str, Any] = value if isinstance(value, dict) else {"value": value}

        try:
            existing = self.client.get_state(
                agent_id=self.agent_id,
                session_id=key,
            )
            self.client.update_state(
                agent_id=self.agent_id,
                data=data,
                version=existing.version,
                session_id=key,
            )
        except MnemoraNotFoundError:
            self.client.store_state(
                agent_id=self.agent_id,
                data=data,
                session_id=key,
            )

    def load(self, key: str) -> dict[str, Any] | None:
        """Retrieve the value stored under *key*.

        Args:
            key: Storage key to look up.

        Returns:
            The stored dict, or ``None`` when the key does not exist.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        try:
            state = self.client.get_state(
                agent_id=self.agent_id,
                session_id=key,
            )
            return state.data
        except MnemoraNotFoundError:
            return None

    def delete(self, key: str) -> None:
        """Remove the value stored under *key*.

        This operation is idempotent: deleting a non-existent key is a no-op.

        Args:
            key: Storage key to remove.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        with contextlib.suppress(MnemoraNotFoundError):
            self.client.delete_state(
                agent_id=self.agent_id,
                session_id=key,
            )

    def list_keys(self) -> list[str]:
        """Return all keys currently stored for this storage instance.

        Returns:
            List of session ID strings that serve as storage keys.  May be
            empty when nothing has been saved yet.
        """
        return self.client.list_sessions(self.agent_id)

    # ------------------------------------------------------------------
    # Optional CrewAI Storage extension points
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Remove all stored keys for this storage instance.

        Iterates over ``list_keys()`` and deletes each one.  If deletion of
        a key fails because it was concurrently removed, the error is
        silently ignored so the overall reset remains idempotent.
        """
        from mnemora.exceptions import MnemoraNotFoundError

        for key in self.list_keys():
            with contextlib.suppress(MnemoraNotFoundError):
                self.client.delete_state(
                    agent_id=self.agent_id,
                    session_id=key,
                )

    def search(self, query: str) -> list[dict[str, Any]]:
        """Return all stored values (full-scan; query argument is unused).

        CrewAI's ``Storage`` interface defines a ``search`` method.  Mnemora
        working memory does not support free-text search within state records.
        This implementation returns every stored value so that callers that
        filter client-side still work correctly.

        Args:
            query: Unused — present for interface compatibility only.

        Returns:
            List of stored data dicts, one per key.
        """
        results: list[dict[str, Any]] = []
        for key in self.list_keys():
            item = self.load(key)
            if item is not None:
                results.append(item)
        return results
