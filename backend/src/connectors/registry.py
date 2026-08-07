"""
backend/src/connectors/registry.py

ConnectorRegistry — discovers and manages all registered connectors.

Connectors register themselves at import time via @ConnectorRegistry.register.
Workers and services look up connectors by name through the registry.

Phase 1: This contract only.
Phase 3: Concrete connector implementations populate this registry.

Usage (Phase 3):
    from backend.src.connectors.registry import ConnectorRegistry

    @ConnectorRegistry.register
    class JobindexConnector(BaseConnector):
        name = "jobindex"
        ...

    # Elsewhere:
    connector = ConnectorRegistry.get("jobindex")
    jobs = await connector.search("data scientist", location="Copenhagen")
"""
from __future__ import annotations

from typing import ClassVar, Type

from core.interfaces.connector import BaseConnector
from core.exceptions import ConnectorNotFoundError


class ConnectorRegistry:
    """
    Central registry for all Helios job portal connectors.

    Connectors are registered via the @ConnectorRegistry.register decorator.
    The registry is a class-level singleton — no instantiation needed.
    """

    _connectors: ClassVar[dict[str, BaseConnector]] = {}

    @classmethod
    def register(cls, connector_class: Type[BaseConnector]) -> Type[BaseConnector]:
        """
        Decorator that registers a connector class by its name.

        Args:
            connector_class: A concrete subclass of BaseConnector.

        Returns:
            The connector class unchanged (for use as a decorator).

        Raises:
            ValueError: If a connector with that name is already registered.
        """
        name = connector_class.name
        if name in cls._connectors:
            raise ValueError(
                f"Connector '{name}' is already registered. "
                f"Each connector must have a unique name."
            )
        cls._connectors[name] = connector_class()
        return connector_class

    @classmethod
    def get(cls, name: str) -> BaseConnector:
        """
        Retrieve a registered connector by name.

        Args:
            name: Connector identifier, e.g. "jobindex".

        Returns:
            The connector instance.

        Raises:
            ConnectorNotFoundError: If no connector is registered with that name.
        """
        if name not in cls._connectors:
            raise ConnectorNotFoundError(
                f"No connector registered for '{name}'. "
                f"Available: {list(cls._connectors.keys())}"
            )
        return cls._connectors[name]

    @classmethod
    def all(cls) -> dict[str, BaseConnector]:
        """Return all registered connectors keyed by name."""
        return dict(cls._connectors)

    @classmethod
    def names(cls) -> list[str]:
        """Return names of all registered connectors."""
        return list(cls._connectors.keys())
