"""
core/interfaces/connector.py

BaseConnector — the contract every job portal integration must implement.

Connectors live in backend/src/connectors/.
They are called by workers and services.
The frontend never calls connectors directly.

Implementation phases:
  Phase 1: This contract only.
  Phase 3: First connector implementations (Greenhouse, Lever, Wellfound, …).
  Existing CLIs (.agents/skills/*/cli/) remain as-is and are wrapped
  in Phase 3 connector implementations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.models.job import Job


class BaseConnector(ABC):
    """
    Abstract base for all Helios job portal connectors.

    Every connector MUST implement search(), fetch(), and normalize().
    health_check() has a default implementation that always returns True;
    override it per connector to test real reachability.
    """

    #: Connector identifier, e.g. "jobindex", "greenhouse".
    #: Must match the JobSource enum value.
    name: str

    #: Base URL of the target portal.
    source_url: str

    @abstractmethod
    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs,
    ) -> list[Job]:
        """
        Search the portal for jobs matching the query.

        Args:
            query: Search terms (role title, skill, keyword).
            location: City, region, or country filter. None = no filter.
            max_results: Upper bound on returned jobs.
            **kwargs: Connector-specific options (date_range, remote_only, etc.)

        Returns:
            List of normalized Job objects. May be empty. Never raises on
            partial results — return what is available and log failures.
        """
        ...

    @abstractmethod
    async def fetch(self, source_id: str) -> Job:
        """
        Fetch complete job details for a single job by the portal's own ID.

        Args:
            source_id: The portal-native job identifier.

        Returns:
            A fully populated Job object.

        Raises:
            ConnectorError: If the job cannot be retrieved.
            JobNotFoundError: If the job no longer exists on the portal.
        """
        ...

    @abstractmethod
    def normalize(self, raw: dict) -> Job:
        """
        Convert portal-specific raw payload into the universal Job model.

        Called internally by search() and fetch(). Must never raise on
        missing or malformed fields — use defaults from the Job model.

        Args:
            raw: Portal-native job data (JSON response, parsed HTML, etc.)

        Returns:
            A Job with as many fields populated as the raw data allows.
        """
        ...

    async def health_check(self) -> bool:
        """
        Verify the portal is reachable and responding.

        Override this per connector to make a lightweight request
        (e.g., fetch the homepage or a known stable endpoint).

        Returns:
            True if healthy, False otherwise. Does not raise.
        """
        return True
