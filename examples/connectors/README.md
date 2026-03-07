# Mnemora Connector Framework

Build integrations that sync CRM/ERP data into Mnemora memory for AI agents.

## Available Connectors

| Connector | Status | Auth Type |
|-----------|--------|-----------|
| HubSpot | Working | API Key |
| Salesforce | Stub | OAuth2 |
| Odoo | Stub | Basic |
| Zoho CRM | Stub | OAuth2 |

## Quick Start

```python
from mnemora import MnemoraSync
from registry import ConnectorRegistry

# Discover all connectors
ConnectorRegistry.discover()

# Use a connector directly
with MnemoraSync(api_key="mnm_...") as client:
    HubSpot = ConnectorRegistry.get("hubspot")
    connector = HubSpot(client, hubspot_token="pat-na1-...")

    if connector.test_connection():
        result = connector.sync_all(agent_id="crm-agent")
        print(f"Synced {result.total_synced} objects in {result.duration_seconds:.1f}s")
```

## Using the Sync Engine

```python
from mnemora import MnemoraSync
from sync_engine import SyncEngine
from registry import ConnectorRegistry

ConnectorRegistry.discover()

with MnemoraSync(api_key="mnm_...") as client:
    engine = SyncEngine(client)
    engine.add("hubspot", hubspot_token="pat-na1-...")

    # Sync one connector
    result = engine.sync("hubspot", agent_id="crm-agent")

    # Or sync all configured connectors
    results = engine.sync_all(agent_id="crm-agent")
```

## Building a New Connector

### 1. Create the directory

```
connectors/
└── mycrm/
    ├── __init__.py
    ├── connector.py
    └── config.py
```

### 2. Define the connector class

```python
# mycrm/connector.py
from base_connector import BaseConnector, ConnectorStatus
from registry import ConnectorRegistry

@ConnectorRegistry.register
class MyCRMConnector(BaseConnector):
    name = "mycrm"
    display_name = "My CRM"
    description = "Sync data from My CRM"
    icon = "🔵"
    supported_objects = ["contacts", "companies", "deals", "tickets"]
    auth_type = "api_key"
    docs_url = "https://docs.mycrm.com"

    def __init__(self, mnemora_client, **kwargs):
        super().__init__(mnemora_client, **kwargs)
        self._token = kwargs.get("api_token", "")

    def test_connection(self) -> bool:
        # Call your CRM API to verify credentials
        ...

    def sync_contacts(self, agent_id: str) -> int:
        # Fetch contacts, store as semantic memory
        contacts = self._fetch_contacts()
        for c in contacts:
            self.mnemora.store_memory(
                agent_id=agent_id,
                content=f"Contact: {c['name']}, Email: {c['email']}",
                namespace="contacts",
                metadata={"type": "contact", "source": "mycrm"},
            )
        return len(contacts)

    def sync_companies(self, agent_id: str) -> int: ...
    def sync_deals(self, agent_id: str) -> int: ...
    def sync_tickets(self, agent_id: str) -> int: ...
    def get_status(self): return self._status
    def get_config_schema(self): return {"type": "object", "properties": {...}}
```

### 3. Memory type mapping

| CRM Object | Mnemora Memory | Why |
|------------|---------------|-----|
| Contacts | Semantic | Vector-searchable by name, email, company |
| Companies | Semantic | Vector-searchable by name, industry |
| Deals | Semantic + State | Searchable context + live pipeline status |
| Tickets | Episodic | Time-series event log |

### 4. Add to discovery

Add your module name to the `discover()` list in `registry.py`.
