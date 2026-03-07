from __future__ import annotations
from dataclasses import dataclass

@dataclass
class OdooConfig:
    url: str
    database: str
    username: str
    api_key: str
