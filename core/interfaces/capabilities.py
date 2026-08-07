"""
core/interfaces/capabilities.py

ConnectorCapabilities Pydantic model.
Allows connectors to advertise which portal features they support.
"""
from __future__ import annotations

from pydantic import BaseModel


class ConnectorCapabilities(BaseModel):
    """Configuration capabilities advertised by each portal connector."""

    supports_search: bool = True
    supports_incremental_sync: bool = False
    supports_salary: bool = False
    supports_remote_filter: bool = False
    supports_company_lookup: bool = False
    supports_pagination: bool = False

    model_config = {"frozen": True}
