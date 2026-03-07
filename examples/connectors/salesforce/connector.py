"""Salesforce CRM connector — stub implementation."""

from __future__ import annotations

from typing import Any

from mnemora import MnemoraSync

from base_connector import BaseConnector, ConnectorStatus
from registry import ConnectorRegistry

_NOT_IMPLEMENTED = "Salesforce connector coming soon. See https://mnemora.dev/docs/integrations"


@ConnectorRegistry.register
class SalesforceConnector(BaseConnector):
    name = "salesforce"
    display_name = "Salesforce"
    description = "Sync contacts, accounts, opportunities, and cases from Salesforce"
    icon = "☁️"
    supported_objects = ["contacts", "accounts", "opportunities", "cases"]
    auth_type = "oauth2"
    docs_url = "https://developer.salesforce.com/docs/atlas.en-us.api_rest.meta/api_rest/"

    def __init__(self, mnemora_client: MnemoraSync, **kwargs: Any) -> None:
        super().__init__(mnemora_client, **kwargs)
        self._client_id = kwargs.get("client_id", "")
        self._client_secret = kwargs.get("client_secret", "")
        self._instance_url = kwargs.get("instance_url", "")

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
                "client_id": {"type": "string", "title": "Client ID", "description": "Salesforce Connected App client ID"},
                "client_secret": {"type": "string", "title": "Client Secret", "description": "Salesforce Connected App client secret"},
                "instance_url": {"type": "string", "title": "Instance URL", "description": "e.g. https://yourorg.my.salesforce.com"},
            },
            "required": ["client_id", "client_secret", "instance_url"],
        }
