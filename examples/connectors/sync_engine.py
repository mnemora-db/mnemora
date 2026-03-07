"""Sync engine — orchestrates sync across multiple connectors.

Usage::

    from mnemora import MnemoraSync
    from sync_engine import SyncEngine

    with MnemoraSync(api_key="mnm_...") as client:
        engine = SyncEngine(client)
        engine.add("hubspot", hubspot_token="pat-na1-...")

        # Sync one connector
        result = engine.sync("hubspot", agent_id="crm-agent")

        # Sync all configured connectors
        results = engine.sync_all(agent_id="crm-agent")
"""

from __future__ import annotations

from typing import Any

from mnemora import MnemoraSync
from rich.console import Console
from rich.table import Table

from base_connector import BaseConnector, SyncResult
from registry import ConnectorRegistry

console = Console()


class SyncEngine:
    """Orchestrates sync across multiple configured connectors."""

    def __init__(self, mnemora_client: MnemoraSync) -> None:
        self.mnemora = mnemora_client
        self._instances: dict[str, BaseConnector] = {}

    def add(self, connector_name: str, **kwargs: Any) -> None:
        """Instantiate and register a connector by name.

        Args:
            connector_name: Registry name (e.g. "hubspot").
            **kwargs: Connector-specific config (e.g. hubspot_token).
        """
        ConnectorClass = ConnectorRegistry.get(connector_name)
        instance = ConnectorClass(self.mnemora, **kwargs)

        if instance.test_connection():
            console.print(
                f"[green]Connected:[/] {instance.display_name} ({instance.name})"
            )
        else:
            console.print(
                f"[yellow]Warning:[/] {instance.display_name} connection test failed"
            )

        self._instances[connector_name] = instance

    def sync(self, connector_name: str, agent_id: str) -> SyncResult:
        """Run sync for a single connector.

        Args:
            connector_name: Which connector to sync.
            agent_id: Mnemora agent_id to store data under.

        Returns:
            SyncResult with counts and timing.
        """
        if connector_name not in self._instances:
            raise KeyError(
                f"Connector '{connector_name}' not configured. "
                f"Call engine.add('{connector_name}', ...) first."
            )

        instance = self._instances[connector_name]
        console.print(f"\n[cyan]Syncing {instance.display_name}...[/]")

        result = instance.sync_all(agent_id)
        self._print_result(result)
        return result

    def sync_all(self, agent_id: str) -> list[SyncResult]:
        """Run sync for all configured connectors.

        Args:
            agent_id: Mnemora agent_id to store data under.

        Returns:
            List of SyncResult, one per connector.
        """
        results: list[SyncResult] = []

        for name, instance in self._instances.items():
            console.print(f"\n[cyan]Syncing {instance.display_name}...[/]")
            result = instance.sync_all(agent_id)
            self._print_result(result)
            results.append(result)

        if results:
            self._print_summary(results)

        return results

    def list_connectors(self) -> list[str]:
        """Return names of all configured connectors."""
        return list(self._instances.keys())

    def _print_result(self, result: SyncResult) -> None:
        """Print a single sync result."""
        status = "[green]OK[/]" if result.success else "[red]ERRORS[/]"
        console.print(
            f"  {status} | "
            f"contacts={result.contacts_synced} "
            f"companies={result.companies_synced} "
            f"deals={result.deals_synced} "
            f"tickets={result.tickets_synced} "
            f"| {result.duration_seconds:.1f}s"
        )
        for err in result.errors:
            console.print(f"  [red]Error:[/] {err}")

    def _print_summary(self, results: list[SyncResult]) -> None:
        """Print a summary table for all sync results."""
        table = Table(title="Sync Summary", show_lines=True)
        table.add_column("Connector", width=16)
        table.add_column("Contacts", justify="right", width=10)
        table.add_column("Companies", justify="right", width=10)
        table.add_column("Deals", justify="right", width=10)
        table.add_column("Tickets", justify="right", width=10)
        table.add_column("Duration", justify="right", width=10)
        table.add_column("Status", width=8)

        for r in results:
            status = "[green]OK[/]" if r.success else f"[red]{len(r.errors)} err[/]"
            table.add_row(
                r.connector_name,
                str(r.contacts_synced),
                str(r.companies_synced),
                str(r.deals_synced),
                str(r.tickets_synced),
                f"{r.duration_seconds:.1f}s",
                status,
            )

        console.print()
        console.print(table)
