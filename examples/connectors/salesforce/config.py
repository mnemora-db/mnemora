from __future__ import annotations
from dataclasses import dataclass

@dataclass
class SalesforceConfig:
    client_id: str
    client_secret: str
    instance_url: str
