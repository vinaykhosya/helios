"""
backend/src/connectors/greenhouse.py

GreenhouseConnector implementation of core.interfaces.BaseConnector.
Adapts Greenhouse boards API payloads to the universal Job format.
"""
from __future__ import annotations

from typing import Optional
import httpx
from pydantic import BaseModel, Field
from core.models.job import Job, JobSource
from core.interfaces import BaseConnector, ConnectorCapabilities
from core.exceptions import ConnectorError, JobNotFoundError


class GreenhouseJob(BaseModel):
    """Pydantic representation of the raw Greenhouse job board schema."""

    id: int
    title: str
    content: Optional[str] = ""
    updated_at: Optional[str] = ""
    absolute_url: Optional[str] = ""
    location: Optional[dict] = Field(default_factory=dict)
    metadata: Optional[list] = Field(default_factory=list)


class GreenhouseConnector(BaseConnector):
    """Greenhouse Job Board Connector Adapter."""

    name = "greenhouse"
    source_url = "https://boards-api.greenhouse.io"

    capabilities = ConnectorCapabilities(
        supports_search=True,
        supports_incremental_sync=False,
        supports_salary=False,
        supports_remote_filter=False,
        supports_company_lookup=False,
        supports_pagination=False,
    )

    def __init__(self, board_token: str = "google"):
        self.board_token = board_token
        self.client = httpx.AsyncClient(timeout=10.0)

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs,
    ) -> list[Job]:
        """Query the public Greenhouse API list endpoint."""
        url = f"{self.source_url}/v1/boards/{self.board_token}/jobs"
        try:
            res = await self.client.get(url)
            if res.status_code == 404:
                return []
            res.raise_for_status()
            data = res.json()
            raw_jobs = data.get("jobs", [])

            # Filter and normalize
            jobs = []
            for r in raw_jobs:
                # 1. Parse into GreenhouseJob schema for validation
                try:
                    gh_job = GreenhouseJob(**r)
                except Exception as e:
                    print(f"Greenhouse validation fail for job {r.get('id')}: {e}")
                    continue

                # Query filter (case-insensitive substring match)
                if query.lower() not in gh_job.title.lower():
                    continue

                # Location filter
                loc_name = gh_job.location.get("name", "")
                if location and location.lower() not in loc_name.lower():
                    continue

                # 2. Normalize to universal Job
                jobs.append(self.normalize(gh_job.model_dump()))

                if len(jobs) >= max_results:
                    break

            return jobs
        except Exception as e:
            print(f"Greenhouse search fail: {e}")
            return []

    async def fetch(self, source_id: str) -> Job:
        """Query the public Greenhouse API details endpoint for a single job."""
        url = f"{self.source_url}/v1/boards/{self.board_token}/jobs/{source_id}"
        try:
            res = await self.client.get(url)
            if res.status_code == 404:
                raise JobNotFoundError(f"Greenhouse job not found: {source_id}")
            res.raise_for_status()
            data = res.json()

            # Parse and normalize
            gh_job = GreenhouseJob(**data)
            return self.normalize(gh_job.model_dump())
        except JobNotFoundError:
            raise
        except Exception as e:
            raise ConnectorError(f"Greenhouse fetch failed for ID {source_id}: {e}") from e

    def normalize(self, raw: dict) -> Job:
        """Translate GreenhouseJob model dump to universal Job model."""
        loc_name = raw.get("location", {}).get("name", "")

        # Default properties
        return Job(
            source=JobSource.GREENHOUSE,
            source_id=str(raw.get("id")),
            source_url=raw.get("absolute_url") or f"https://boards.greenhouse.io/{self.board_token}/jobs/{raw.get('id')}",
            title=raw.get("title", "Untitled Job"),
            company=self.board_token.capitalize(),  # Use board token capitalization as company name
            location=loc_name,
            description=raw.get("content", ""),
            raw_data=raw,
        )

    async def health_check(self) -> bool:
        """Validate if the Greenhouse board token exists and responds."""
        url = f"{self.source_url}/v1/boards/{self.board_token}"
        try:
            res = await self.client.get(url)
            return res.status_code == 200
        except Exception:
            return False
