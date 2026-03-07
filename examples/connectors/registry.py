"""Connector registry — discovers and manages available connectors."""

from __future__ import annotations

from typing import Any

from base_connector import BaseConnector


class ConnectorRegistry:
    """Discovers and manages available connectors.

    Usage::

        from registry import ConnectorRegistry

        # Auto-discover all connectors
        ConnectorRegistry.discover()

        # List available connectors
        for c in ConnectorRegistry.list_all():
            print(c["name"], c["display_name"])

        # Instantiate a connector
        ConnectorClass = ConnectorRegistry.get("hubspot")
        connector = ConnectorClass(mnemora_client, hubspot_token="...")
    """

    _connectors: dict[str, type[BaseConnector]] = {}

    @classmethod
    def register(cls, connector_class: type[BaseConnector]) -> type[BaseConnector]:
        """Class decorator to register a connector.

        Example::

            @ConnectorRegistry.register
            class MyConnector(BaseConnector):
                name = "my_connector"
                ...
        """
        cls._connectors[connector_class.name] = connector_class
        return connector_class

    @classmethod
    def get(cls, name: str) -> type[BaseConnector]:
        """Look up a connector class by name.

        Raises:
            KeyError: If the connector is not registered.
        """
        if name not in cls._connectors:
            available = list(cls._connectors.keys())
            raise KeyError(
                f"Connector '{name}' not registered. Available: {available}"
            )
        return cls._connectors[name]

    @classmethod
    def list_all(cls) -> list[dict[str, Any]]:
        """Return metadata for all registered connectors."""
        return [
            {
                "name": c.name,
                "display_name": c.display_name,
                "description": c.description,
                "icon": c.icon,
                "supported_objects": c.supported_objects,
                "auth_type": c.auth_type,
                "docs_url": c.docs_url,
            }
            for c in cls._connectors.values()
        ]

    @classmethod
    def discover(cls) -> None:
        """Import all connector modules to trigger registration.

        Each connector module uses the @ConnectorRegistry.register
        decorator at class definition time.
        """
        import importlib

        for module_name in ["hubspot", "salesforce", "odoo", "zoho"]:
            try:
                importlib.import_module(f"{module_name}.connector")
            except ImportError:
                pass
