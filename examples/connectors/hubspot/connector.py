"""HubSpot CRM connector — syncs contacts, companies, deals, tickets to Mnemora."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from mnemora import MnemoraSync

from base_connector import BaseConnector, ConnectorStatus
from registry import ConnectorRegistry

HUBSPOT_API_BASE = "https://api.hubapi.com"


@ConnectorRegistry.register
class HubSpotConnector(BaseConnector):
    name = "hubspot"
    display_name = "HubSpot"
    description = "Sync contacts, companies, deals, and tickets from HubSpot CRM"
    icon = "🟠"
    supported_objects = ["contacts", "companies", "deals", "tickets"]
    auth_type = "api_key"
    docs_url = "https://developers.hubspot.com/docs/api/overview"

    def __init__(self, mnemora_client: MnemoraSync, **kwargs: Any) -> None:
        super().__init__(mnemora_client, **kwargs)
        self._token = kwargs.get("hubspot_token", "")
        self._http = httpx.Client(
            base_url=HUBSPOT_API_BASE,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=30.0,
        )

    def _get_objects(self, object_type: str, properties: list[str]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        params: dict[str, Any] = {"properties": ",".join(properties), "limit": 100}
        url = f"/crm/v3/objects/{object_type}"
        while True:
            resp = self._http.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results", []))
            paging = data.get("paging", {}).get("next")
            if paging and paging.get("after"):
                params["after"] = paging["after"]
            else:
                break
        return results

    def test_connection(self) -> bool:
        try:
            resp = self._http.get("/crm/v3/objects/contacts", params={"limit": 1})
            self._status = ConnectorStatus.CONNECTED if resp.status_code == 200 else ConnectorStatus.ERROR
            return resp.status_code == 200
        except Exception:
            self._status = ConnectorStatus.ERROR
            return False

    def sync_contacts(self, agent_id: str) -> int:
        contacts = self._get_objects("contacts", ["firstname", "lastname", "email", "phone", "company", "lifecyclestage", "jobtitle"])
        for c in contacts:
            p = c.get("properties", {})
            name = f"{p.get('firstname', '')} {p.get('lastname', '')}".strip() or "Unknown"
            self.mnemora.store_memory(
                agent_id=agent_id,
                content=f"Contact: {name}, Email: {p.get('email', 'N/A')}, Company: {p.get('company', 'N/A')}, Phone: {p.get('phone', 'N/A')}, Title: {p.get('jobtitle', 'N/A')}, Lifecycle: {p.get('lifecyclestage', 'N/A')}",
                namespace="contacts",
                metadata={"hubspot_id": c["id"], "type": "contact", "name": name},
            )
        return len(contacts)

    def sync_companies(self, agent_id: str) -> int:
        companies = self._get_objects("companies", ["name", "industry", "annualrevenue", "numberofemployees", "website", "description"])
        for c in companies:
            p = c.get("properties", {})
            name = p.get("name") or "Unknown"
            self.mnemora.store_memory(
                agent_id=agent_id,
                content=f"Company: {name}, Industry: {p.get('industry', 'N/A')}, Revenue: {p.get('annualrevenue', 'N/A')}, Employees: {p.get('numberofemployees', 'N/A')}, Website: {p.get('website', 'N/A')}",
                namespace="companies",
                metadata={"hubspot_id": c["id"], "type": "company", "name": name},
            )
        return len(companies)

    def sync_deals(self, agent_id: str) -> int:
        deals = self._get_objects("deals", ["dealname", "amount", "dealstage", "pipeline", "closedate", "hubspot_owner_id"])
        for d in deals:
            p = d.get("properties", {})
            name = p.get("dealname") or "Unnamed Deal"
            self.mnemora.store_memory(
                agent_id=agent_id,
                content=f"Deal: {name}, Amount: ${p.get('amount', 'N/A')}, Stage: {p.get('dealstage', 'N/A')}, Pipeline: {p.get('pipeline', 'default')}, Close Date: {p.get('closedate', 'N/A')}",
                namespace="deals",
                metadata={"hubspot_id": d["id"], "type": "deal", "name": name, "stage": p.get("dealstage", "")},
            )
            self.mnemora.store_state(
                agent_id=agent_id,
                data={"deal_name": name, "amount": p.get("amount", ""), "stage": p.get("dealstage", ""), "closedate": p.get("closedate", ""), "synced_at": datetime.now(timezone.utc).isoformat()},
                session_id=f"deal-{d['id']}",
            )
        return len(deals)

    def sync_tickets(self, agent_id: str) -> int:
        tickets = self._get_objects("tickets", ["subject", "content", "hs_pipeline_stage", "hs_ticket_priority", "createdate"])
        for t in tickets:
            p = t.get("properties", {})
            self.mnemora.store_episode(
                agent_id=agent_id,
                session_id=f"ticket-{t['id']}",
                type="observation",
                content={"subject": p.get("subject", ""), "body": p.get("content", ""), "status": p.get("hs_pipeline_stage", ""), "priority": p.get("hs_ticket_priority", "MEDIUM"), "created_date": p.get("createdate", "")},
                metadata={"hubspot_id": t["id"], "type": "ticket"},
            )
        return len(tickets)

    def get_status(self) -> ConnectorStatus:
        return self._status

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hubspot_token": {"type": "string", "title": "Private App Token", "description": "HubSpot Private App access token (Settings > Integrations > Private Apps)"},
            },
            "required": ["hubspot_token"],
        }
