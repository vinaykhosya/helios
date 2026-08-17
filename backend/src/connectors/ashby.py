"""
backend/src/connectors/ashby.py

AshbyConnector -- fetches public job listings from Ashby's job board API.

Ashby is a modern ATS used by companies like Linear, Vercel, Notion, Retool, etc.
The public posting API requires no auth key -- just the company slug.

API: GET https://api.ashbyhq.com/posting-api/job-board/{companySlug}
Docs: https://developers.ashby.com/docs/api/posting-api

Friction: LOW (score=1) -- Ashby forms are clean, single-page, minimal friction.
"""
from __future__ import annotations

from typing import Optional
import httpx

from core.models.job import Job, JobSource
from core.interfaces import BaseConnector, ConnectorCapabilities
from core.exceptions import ConnectorError, JobNotFoundError


class AshbyNormalizer:
    """Normalizes Ashby API postings to the universal Job model."""

    @staticmethod
    def normalize(posting: dict, company_slug: str) -> Job:
        location_raw = posting.get("location", "") or ""
        description = (posting.get("descriptionSafe") or posting.get("descriptionPlain") or "")[:3000]
        apply_url = posting.get("applyUrl") or posting.get("jobUrl") or ""
        hosted_url = posting.get("jobUrl", "") or apply_url

        published_raw = posting.get("publishedDate") or posting.get("publishedAt") or posting.get("createdAt")
        updated_raw = posting.get("updatedAt")

        from intelligence.freshness.gate import parse_timestamp, FreshnessGate
        posted_dt, conf, anomaly = parse_timestamp(published_raw)
        updated_dt, _, _ = parse_timestamp(updated_raw)

        job = Job(
            source=JobSource.ASHBY,
            source_id=str(posting.get("id", "")),
            source_url=hosted_url,
            title=posting.get("title", "Untitled"),
            company=posting.get("companyName") or company_slug.capitalize(),
            location=location_raw,
            description=description,
            apply_url=apply_url,
            posted_at=posted_dt,
            posted_date=posted_dt,
            last_updated_at=updated_dt,
            freshness_confidence=conf,
            freshness_source="ashby",
            raw_data=posting,
        )
        gate = FreshnessGate()
        return gate.evaluate_job(job)


class AshbyConnector(BaseConnector):
    """
    Ashby Job Board Connector.
    Fetches listings from Ashby's public posting API for a given company slug.
    """

    name = "ashby"
    source_url = "https://api.ashbyhq.com/posting-api/job-board"

    capabilities = ConnectorCapabilities(
        supports_search=True,
        supports_incremental_sync=False,
        supports_salary=False,
        supports_remote_filter=False,
        supports_company_lookup=False,
        supports_pagination=False,
    )

    def __init__(self, site: str = "linear"):
        self.site = site
        self.client = httpx.AsyncClient(timeout=15.0)

    async def search(
        self,
        query: str = "",
        location: Optional[str] = None,
        max_results: int = 50,
        **kwargs,
    ) -> list[Job]:
        """Fetch all public postings for the company, then filter by query/location."""
        url = f"{self.source_url}/{self.site}"
        try:
            resp = await self.client.get(url)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            data = resp.json()

            # Ashby returns either {"jobs": [...]} or a direct list
            postings = data.get("jobs", []) if isinstance(data, dict) else data

            jobs: list[Job] = []
            for p in postings:
                try:
                    title = p.get("title", "")
                    # Query filter
                    if query and query.lower() not in title.lower():
                        continue
                    # Location filter
                    if location:
                        post_location = (p.get("location") or "").lower()
                        if location.lower() not in post_location:
                            continue

                    job = AshbyNormalizer.normalize(p, self.site)
                    jobs.append(job)

                    if len(jobs) >= max_results:
                        break
                except Exception as e:
                    print(f"[Ashby] Normalization failed for posting {p.get('id')}: {e}")
                    continue

            return jobs
        except Exception as e:
            print(f"[Ashby] search failed for site={self.site}: {e}")
            return []

    async def fetch(self, source_id: str) -> Job:
        """Fetch a single posting by its ID."""
        # Ashby doesn't expose a single-posting endpoint in the public API.
        # Fetch all and find by source_id.
        jobs = await self.search(query="")
        for job in jobs:
            if job.source_id == source_id:
                return job
        raise JobNotFoundError(f"Ashby job not found: site={self.site} id={source_id}")

    def normalize(self, raw: dict) -> Job:
        """Adapter bridge translating raw payload using AshbyNormalizer."""
        return AshbyNormalizer.normalize(raw, self.site)

    async def health_check(self) -> bool:
        """Verify the Ashby site is accessible."""
        try:
            resp = await self.client.get(f"{self.source_url}/{self.site}")
            return resp.status_code == 200
        except Exception:
            return False
