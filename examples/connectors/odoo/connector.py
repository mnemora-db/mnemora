"""Odoo ERP connector — stub implementation."""

from __future__ import annotations

from typing import Any

from mnemora import MnemoraSync

from base_connector import BaseConnector, ConnectorStatus
from registry import ConnectorRegistry

_NOT_IMPLEMENTED = "Odoo connector coming soon. See https://mnemora.dev/docs/integrations"


@ConnectorRegistry.register
class OdooConnector(BaseConnector):
    name = "odoo"
    display_name = "Odoo"
    description = "Sync partners, leads, tickets, and orders from Odoo ERP"
    icon = "🟣"
    supported_objects = ["res.partner", "crm.lead", "helpdesk.ticket", "sale.order"]
    auth_type = "basic"
    docs_url = "https://www.odoo.com/documentation/17.0/developer/reference/external_api.html"

    def __init__(self, mnemora_client: MnemoraSync, **kwargs: Any) -> None:
        super().__init__(mnemora_client, **kwargs)
        self._url = kwargs.get("url", "")
        self._database = kwargs.get("database", "")
        self._username = kwargs.get("username", "")
        self._api_key = kwargs.get("api_key", "")

    def test_connection(self) -> bool:
        return False

    def sync_contacts(self, agent_id: str) -> int:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def sync_companies(self, agent_id: str) -> int:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def sync_deals(self, agent_id: str) -> int:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def sync_tickets(self, agent_id: str) -> int:
        raise NotImplementedError(_NOT_IMPLEMENTED)

    def get_status(self) -> ConnectorStatus:
        return ConnectorStatus.DISCONNECTED

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "url": {"type": "string", "title": "Odoo URL", "description": "e.g. https://mycompany.odoo.com"},
                "database": {"type": "string", "title": "Database", "description": "Odoo database name"},
                "username": {"type": "string", "title": "Username", "description": "Odoo login username"},
                "api_key": {"type": "string", "title": "API Key", "description": "Odoo API key (Settings > Users > API Keys)"},
            },
            "required": ["url", "database", "username", "api_key"],
        }
