from __future__ import annotations
from dataclasses import dataclass

@dataclass
class ZohoConfig:
    client_id: str
    client_secret: str
    refresh_token: str
