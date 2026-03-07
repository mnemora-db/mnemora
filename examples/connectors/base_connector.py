"""Abstract base class for all CRM/ERP connectors.

Every connector must inherit from BaseConnector and implement the abstract
methods.  The sync_all() default implementation calls each sync method in
sequence, catches per-method errors, and returns a SyncResult.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from mnemora import MnemoraSync


class ConnectorStatus(Enum):
    """Runtime status of a connector instance."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    SYNCING = "syncing"
    ERROR = "error"


@dataclass
class SyncResult:
    """Outcome of a sync_all() run."""

    connector_name: str
    contacts_synced: int = 0
    companies_synced: int = 0
    deals_synced: int = 0
    tickets_synced: int = 0
    episodes_created: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def total_synced(self) -> int:
        return (
            self.contacts_synced
            + self.companies_synced
            + self.deals_synced
            + self.tickets_synced
        )

    @property
    def success(self) -> bool:
        return len(self.errors) == 0


class BaseConnector(ABC):
    """Base class for all CRM/ERP connectors.

    Subclasses MUST define the following class attributes:
        name, display_name, description, icon, supported_objects,
        auth_type, docs_url

    And implement all abstract methods.
    """

    name: str
    display_name: str
    description: str
    icon: str
    supported_objects: list[str]
    auth_type: str  # "api_key", "oauth2", "basic"
    docs_url: str

    def __init__(self, mnemora_client: MnemoraSync, **kwargs: Any) -> None:
        self.mnemora = mnemora_client
        self._status = ConnectorStatus.DISCONNECTED

    @abstractmethod
    def test_connection(self) -> bool:
        """Verify credentials work. Return True if connected."""
        ...

    @abstractmethod
    def sync_contacts(self, agent_id: str) -> int:
        """Sync contacts to Mnemora semantic memory. Return count."""
        ...

    @abstractmethod
    def sync_companies(self, agent_id: str) -> int:
        """Sync companies to Mnemora semantic memory. Return count."""
        ...

    @abstractmethod
    def sync_deals(self, agent_id: str) -> int:
        """Sync deals to Mnemora semantic + state memory. Return count."""
        ...

    @abstractmethod
    def sync_tickets(self, agent_id: str) -> int:
        """Sync tickets to Mnemora episodic memory. Return count."""
        ...

    def sync_all(self, agent_id: str) -> SyncResult:
        """Sync everything. Calls each sync method, catches errors per method."""
        start = time.time()
        result = SyncResult(connector_name=self.name)
        self._status = ConnectorStatus.SYNCING

        # Map supported object names to (sync_method_suffix, result_attr)
        object_map = {
            "contacts": "contacts_synced",
            "companies": "companies_synced",
            "accounts": "companies_synced",  # Salesforce/Zoho call them accounts
            "deals": "deals_synced",
            "opportunities": "deals_synced",  # Salesforce calls them opportunities
            "tickets": "tickets_synced",
            "cases": "tickets_synced",  # Salesforce calls them cases
        }

        for obj in self.supported_objects:
            obj_lower = obj.lower().replace(".", "_")
            # Find the matching sync method
            method_name = f"sync_{obj_lower}"
            attr_name = object_map.get(obj_lower)

            if not hasattr(self, method_name) or attr_name is None:
                continue
            try:
                count = getattr(self, method_name)(agent_id)
                setattr(result, attr_name, getattr(result, attr_name) + count)
            except NotImplementedError:
                pass  # Skip unimplemented methods silently
            except Exception as e:
                result.errors.append(f"{obj}: {e}")

        result.duration_seconds = time.time() - start
        self._status = (
            ConnectorStatus.CONNECTED if not result.errors else ConnectorStatus.ERROR
        )
        return result

    @abstractmethod
    def get_status(self) -> ConnectorStatus:
        """Return current connector status."""
        ...

    @abstractmethod
    def get_config_schema(self) -> dict[str, Any]:
        """Return JSON schema for connector configuration.

        Used by the dashboard UI to render config forms dynamically.
        """
        ...
