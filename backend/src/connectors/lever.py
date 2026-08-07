"""
backend/src/connectors/lever.py

LeverConnector implementation.
Fetches listings from the Lever API and delegates normalization to LeverNormalizer.
"""
from __future__ import annotations

from typing import Optional, Any
import httpx
from pydantic import BaseModel, Field

from core.models.job import Job, JobSource
from core.interfaces import BaseConnector, ConnectorCapabilities
from core.exceptions import ConnectorError, JobNotFoundError


class LeverPosting(BaseModel):
    """Pydantic model representing a raw Lever API posting."""

    id: str
    text: str  # job title
    hostedUrl: str
    createdAt: int
    description: str = ""
    additional: str = ""
    lists: list[dict] = Field(default_factory=list)
    categories: dict[str, Any] = Field(default_factory=dict)


class LeverNormalizer:
    """Normalizes Lever postings to universal Job format."""

    @staticmethod
    def normalize(posting: LeverPosting, site: str) -> Job:
        categories = posting.categories or {}
        location = categories.get("location") or ""
        commitment = categories.get("commitment") or ""

        # Lever descriptions can have both description and additional fields
        description = posting.description
        if posting.additional:
            description += f"\n\n{posting.additional}"

        return Job(
            source=JobSource.LEVER,
            source_id=posting.id,
            source_url=posting.hostedUrl,
            title=posting.text,
            company=site.capitalize(),
            location=location,
            description=description,
            raw_data=posting.model_dump(),
        )


class LeverConnector(BaseConnector):
    """Lever Job Board Connector Adapter."""

    name = "lever"
    source_url = "https://api.lever.co"

    capabilities = ConnectorCapabilities(
        supports_search=True,
        supports_incremental_sync=False,
        supports_salary=False,
        supports_remote_filter=False,
        supports_company_lookup=False,
        supports_pagination=False,
    )

    def __init__(self, site: str = "leverdemo"):
        self.site = site
        self.client = httpx.AsyncClient(timeout=10.0)

    async def search(
        self,
        query: str,
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs,
    ) -> list[Job]:
        """Query public Lever API list endpoint."""
        url = f"{self.source_url}/v0/postings/{self.site}"
        try:
            res = await self.client.get(url)
            if res.status_code == 404:
                return []
            res.raise_for_status()
            raw_postings = res.json()

            jobs = []
            for r in raw_postings:
                try:
                    posting = LeverPosting(**r)
                except Exception as e:
                    print(f"Lever validation fail for job {r.get('id')}: {e}")
                    continue

                # Query filter (case-insensitive substring match)
                if query.lower() not in posting.text.lower():
                    continue

                # Location filter
                loc = posting.categories.get("location", "")
                if location and location.lower() not in loc.lower():
                    continue

                normalized_job = self.normalize(posting.model_dump())
                jobs.append(normalized_job)

                if len(jobs) >= max_results:
                    break

            return jobs
        except Exception as e:
            print(f"Lever search fail: {e}")
            return []

    async def fetch(self, source_id: str) -> Job:
        """Query public Lever API single posting endpoint."""
        url = f"{self.source_url}/v0/postings/{self.site}/{source_id}"
        try:
            res = await self.client.get(url)
            if res.status_code == 404:
                raise JobNotFoundError(f"Lever job not found: {source_id}")
            res.raise_for_status()
            data = res.json()

            posting = LeverPosting(**data)
            return self.normalize(posting.model_dump())
        except JobNotFoundError:
            raise
        except Exception as e:
            raise ConnectorError(f"Lever fetch failed for ID {source_id}: {e}") from e

    def normalize(self, raw: dict) -> Job:
        """Adapter bridge translating raw payload using LeverNormalizer."""
        posting = LeverPosting(**raw)
        return LeverNormalizer.normalize(posting, self.site)

    async def health_check(self) -> bool:
        """Verify the site exists on Lever."""
        url = f"{self.source_url}/v0/postings/{self.site}"
        try:
            res = await self.client.get(url)
            return res.status_code == 200
        except Exception:
            return False
