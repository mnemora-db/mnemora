"""Zoho CRM connector — stub implementation."""

from __future__ import annotations

from typing import Any

from mnemora import MnemoraSync

from base_connector import BaseConnector, ConnectorStatus
from registry import ConnectorRegistry

_NOT_IMPLEMENTED = "Zoho CRM connector coming soon. See https://mnemora.dev/docs/integrations"


@ConnectorRegistry.register
class ZohoConnector(BaseConnector):
    name = "zoho"
    display_name = "Zoho CRM"
    description = "Sync contacts, accounts, deals, and tickets from Zoho CRM"
    icon = "🔴"
    supported_objects = ["Contacts", "Accounts", "Deals", "Tickets"]
    auth_type = "oauth2"
    docs_url = "https://www.zoho.com/crm/developer/docs/api/v7/"

    def __init__(self, mnemora_client: MnemoraSync, **kwargs: Any) -> None:
        super().__init__(mnemora_client, **kwargs)
        self._client_id = kwargs.get("client_id", "")
        self._client_secret = kwargs.get("client_secret", "")
        self._refresh_token = kwargs.get("refresh_token", "")

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
                "client_id": {"type": "string", "title": "Client ID", "description": "Zoho API Console client ID"},
                "client_secret": {"type": "string", "title": "Client Secret", "description": "Zoho API Console client secret"},
                "refresh_token": {"type": "string", "title": "Refresh Token", "description": "OAuth2 refresh token from Zoho authorization flow"},
            },
            "required": ["client_id", "client_secret", "refresh_token"],
        }
