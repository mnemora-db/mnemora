"""HubSpot CRM data sync to Mnemora memory.

Pulls contacts, companies, deals, and tickets from HubSpot REST API
and stores them in the appropriate Mnemora memory tier:
  - Contacts/Companies → semantic memory (vector-searchable)
  - Deals → semantic + state memory (pipeline tracking)
  - Tickets → episodic memory (time-series events)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from mnemora import MnemoraSync
from rich.console import Console
from rich.progress import Progress

logger = logging.getLogger(__name__)
console = Console()

HUBSPOT_API_BASE = "https://api.hubapi.com"


class HubSpotSync:
    """Syncs HubSpot CRM objects into Mnemora memory."""

    def __init__(self, hubspot_token: str, mnemora_client: MnemoraSync) -> None:
        self.hubspot_token = hubspot_token
        self.mnemora = mnemora_client
        self._http = httpx.Client(
            base_url=HUBSPOT_API_BASE,
            headers={"Authorization": f"Bearer {hubspot_token}"},
            timeout=30.0,
        )

    def close(self) -> None:
        """Close the HTTP client."""
        self._http.close()

    def _get_objects(
        self, object_type: str, properties: list[str], limit: int = 100
    ) -> list[dict[str, Any]]:
        """Fetch CRM objects with pagination."""
        all_results: list[dict[str, Any]] = []
        params: dict[str, Any] = {
            "properties": ",".join(properties),
            "limit": limit,
        }
        url = f"/crm/v3/objects/{object_type}"

        while True:
            resp = self._http.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            all_results.extend(data.get("results", []))

            paging = data.get("paging", {}).get("next")
            if paging and paging.get("after"):
                params["after"] = paging["after"]
            else:
                break

        return all_results

    def sync_contacts(self, agent_id: str) -> int:
        """Pull contacts from HubSpot, store each as semantic memory.

        Returns:
            Count of contacts synced.
        """
        properties = [
            "firstname", "lastname", "email", "phone",
            "company", "lifecyclestage", "hubspot_owner_id",
        ]
        contacts = self._get_objects("contacts", properties)
        count = 0

        for contact in contacts:
            props = contact.get("properties", {})
            first = props.get("firstname") or ""
            last = props.get("lastname") or ""
            name = f"{first} {last}".strip() or "Unknown"
            email = props.get("email") or "N/A"
            company = props.get("company") or "N/A"
            phone = props.get("phone") or "N/A"
            lifecycle = props.get("lifecyclestage") or "N/A"
            owner = props.get("hubspot_owner_id") or "Unassigned"

            content = (
                f"Contact: {name}, Email: {email}, Company: {company}, "
                f"Phone: {phone}, Lifecycle: {lifecycle}, Owner: {owner}"
            )
            self.mnemora.store_memory(
                agent_id=agent_id,
                content=content,
                namespace="contacts",
                metadata={
                    "hubspot_id": contact["id"],
                    "type": "contact",
                    "name": name,
                    "email": email,
                    "company": company,
                },
            )
            count += 1

        return count

    def sync_companies(self, agent_id: str) -> int:
        """Pull companies from HubSpot, store as semantic memory.

        Returns:
            Count of companies synced.
        """
        properties = [
            "name", "industry", "annualrevenue",
            "numberofemployees", "website",
        ]
        companies = self._get_objects("companies", properties)
        count = 0

        for company in companies:
            props = company.get("properties", {})
            name = props.get("name") or "Unknown"
            industry = props.get("industry") or "N/A"
            revenue = props.get("annualrevenue") or "N/A"
            employees = props.get("numberofemployees") or "N/A"
            website = props.get("website") or "N/A"

            content = (
                f"Company: {name}, Industry: {industry}, Revenue: {revenue}, "
                f"Employees: {employees}, Website: {website}"
            )
            self.mnemora.store_memory(
                agent_id=agent_id,
                content=content,
                namespace="companies",
                metadata={
                    "hubspot_id": company["id"],
                    "type": "company",
                    "name": name,
                    "industry": industry,
                },
            )
            count += 1

        return count

    def sync_deals(self, agent_id: str) -> int:
        """Pull deals from HubSpot, store as semantic + state memory.

        Semantic memory stores the deal description for search.
        State memory tracks the current pipeline status for active deals.

        Returns:
            Count of deals synced.
        """
        properties = [
            "dealname", "amount", "dealstage",
            "pipeline", "closedate", "hubspot_owner_id",
        ]
        deals = self._get_objects("deals", properties)
        count = 0

        for deal in deals:
            props = deal.get("properties", {})
            name = props.get("dealname") or "Unnamed Deal"
            amount = props.get("amount") or "N/A"
            stage = props.get("dealstage") or "N/A"
            pipeline = props.get("pipeline") or "default"
            closedate = props.get("closedate") or "N/A"
            owner = props.get("hubspot_owner_id") or "Unassigned"

            content = (
                f"Deal: {name}, Amount: ${amount}, Stage: {stage}, "
                f"Pipeline: {pipeline}, Close Date: {closedate}, Owner: {owner}"
            )
            self.mnemora.store_memory(
                agent_id=agent_id,
                content=content,
                namespace="deals",
                metadata={
                    "hubspot_id": deal["id"],
                    "type": "deal",
                    "name": name,
                    "amount": amount,
                    "stage": stage,
                },
            )

            # Also store current pipeline status as working state
            self.mnemora.store_state(
                agent_id=agent_id,
                data={
                    "deal_name": name,
                    "amount": amount,
                    "stage": stage,
                    "pipeline": pipeline,
                    "closedate": closedate,
                    "owner": owner,
                    "hubspot_id": deal["id"],
                    "synced_at": datetime.now(timezone.utc).isoformat(),
                },
                session_id=f"deal-{deal['id']}",
            )
            count += 1

        return count

    def sync_tickets(self, agent_id: str) -> int:
        """Pull tickets from HubSpot, store as episodic memory.

        Each ticket is stored as a time-series event (episode).

        Returns:
            Count of tickets synced.
        """
        properties = [
            "subject", "content", "hs_pipeline_stage",
            "hs_ticket_priority", "createdate",
        ]
        tickets = self._get_objects("tickets", properties)
        count = 0

        for ticket in tickets:
            props = ticket.get("properties", {})
            subject = props.get("subject") or "No subject"
            body = props.get("content") or ""
            stage = props.get("hs_pipeline_stage") or "N/A"
            priority = props.get("hs_ticket_priority") or "MEDIUM"
            created = props.get("createdate") or datetime.now(timezone.utc).isoformat()

            self.mnemora.store_episode(
                agent_id=agent_id,
                session_id=f"ticket-{ticket['id']}",
                type="observation",
                content={
                    "subject": subject,
                    "body": body,
                    "status": stage,
                    "priority": priority,
                    "created_date": created,
                    "hubspot_id": ticket["id"],
                },
                metadata={
                    "hubspot_id": ticket["id"],
                    "type": "ticket",
                    "priority": priority,
                },
            )
            count += 1

        return count

    def sync_all(self, agent_id: str) -> dict[str, int]:
        """Sync all CRM objects to Mnemora.

        Returns:
            Dict with counts per object type.
        """
        results: dict[str, int] = {}

        with Progress(console=console) as progress:
            task = progress.add_task("[cyan]Syncing HubSpot → Mnemora...", total=4)

            progress.update(task, description="[cyan]Syncing contacts...")
            results["contacts"] = self.sync_contacts(agent_id)
            progress.advance(task)

            progress.update(task, description="[cyan]Syncing companies...")
            results["companies"] = self.sync_companies(agent_id)
            progress.advance(task)

            progress.update(task, description="[cyan]Syncing deals...")
            results["deals"] = self.sync_deals(agent_id)
            progress.advance(task)

            progress.update(task, description="[cyan]Syncing tickets...")
            results["tickets"] = self.sync_tickets(agent_id)
            progress.advance(task)

        return results


if __name__ == "__main__":
    import os

    from dotenv import load_dotenv

    load_dotenv()

    hubspot_token = os.environ["HUBSPOT_API_KEY"]
    mnemora_key = os.environ["MNEMORA_API_KEY"]

    with MnemoraSync(api_key=mnemora_key) as client:
        sync = HubSpotSync(hubspot_token, client)
        try:
            results = sync.sync_all(agent_id="hubspot-demo")
            console.print("\n[bold green]Sync complete:[/]")
            for obj_type, count in results.items():
                console.print(f"  {obj_type}: {count}")
        finally:
            sync.close()
