"""
backend/src/connectors/linkedin.py

LinkedInConnector — fetches live public job listings from LinkedIn's guest search API.
Discovers jobs in Delhi, Noida, Gurgaon, Bangalore, India, and Global without requiring authentication.
"""
from __future__ import annotations
import re
import uuid
from typing import Optional
import httpx
from bs4 import BeautifulSoup

from core.models.job import Job, JobSource
from core.interfaces import BaseConnector, ConnectorCapabilities


class LinkedInConnector(BaseConnector):
    """LinkedIn Public Guest Jobs Connector."""

    name = "linkedin"
    source_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    capabilities = ConnectorCapabilities(
        supports_search=True,
        supports_incremental_sync=False,
        supports_salary=False,
        supports_remote_filter=True,
        supports_company_lookup=True,
        supports_pagination=True,
    )

    def __init__(self, location: str = "Delhi, India"):
        self.default_location = location
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(
        self,
        query: str = "Software Engineer",
        location: Optional[str] = None,
        max_results: int = 25,
        **kwargs,
    ) -> list[Job]:
        """Query LinkedIn guest search API."""
        loc = location or self.default_location
        jobs: list[Job] = []

        async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
            for start in range(0, max_results, 10):
                url = f"{self.source_url}?keywords={query}&location={loc}&start={start}"
                try:
                    resp = await client.get(url)
                    if resp.status_code != 200:
                        break

                    soup = BeautifulSoup(resp.text, "html.parser")
                    cards = soup.find_all("li")
                    if not cards:
                        break

                    for card in cards:
                        title_el = card.find("h3", class_="base-search-card__title")
                        company_el = card.find("h4", class_="base-search-card__subtitle")
                        loc_el = card.find("span", class_="job-search-card__location")
                        link_el = card.find("a", class_="base-card__full-link")
                        time_el = card.find("time")

                        if not title_el or not company_el:
                            continue

                        title = title_el.text.strip()
                        company = company_el.text.strip()
                        job_loc = loc_el.text.strip() if loc_el else loc
                        apply_url = link_el["href"] if link_el and "href" in link_el.attrs else ""

                        # Extract Job ID from URL or card
                        urn = card.get("data-entity-urn", "")
                        source_id = urn.split(":")[-1] if urn else str(uuid.uuid4())
                        raw_date = time_el.get("datetime", "") if time_el else (time_el.text.strip() if time_el else "")

                        from intelligence.freshness.gate import parse_timestamp, FreshnessGate
                        posted_dt, conf, _ = parse_timestamp(raw_date)

                        j_obj = Job(
                            id=str(uuid.uuid4()),
                            source=JobSource.LINKEDIN,
                            source_id=source_id,
                            source_url=apply_url,
                            title=title,
                            company=company,
                            location=job_loc,
                            description=f"{title} at {company} in {job_loc}",
                            apply_url=apply_url,
                            posted_at=posted_dt,
                            posted_date=posted_dt,
                            freshness_confidence=conf,
                            freshness_source="linkedin",
                            raw_data={
                                "date": raw_date,
                                "location": job_loc,
                            }
                        )
                        gate = FreshnessGate()
                        jobs.append(gate.evaluate_job(j_obj))

                        if len(jobs) >= max_results:
                            break

                except Exception as e:
                    print(f"[LinkedInConnector] Search error: {e}")
                    break

        return jobs

    def normalize(self, raw: dict) -> Job:
        """Convert raw LinkedIn dictionary into standard Job model."""
        raw_date = raw.get("date") or raw.get("posted_at")
        from intelligence.freshness.gate import parse_timestamp, FreshnessGate
        posted_dt, conf, _ = parse_timestamp(raw_date)

        job = Job(
            id=raw.get("id") or str(uuid.uuid4()),
            source=JobSource.LINKEDIN,
            source_id=raw.get("source_id", str(uuid.uuid4())),
            source_url=raw.get("apply_url", ""),
            title=raw.get("title", "Untitled Role"),
            company=raw.get("company", "Unknown"),
            location=raw.get("location", self.default_location),
            description=raw.get("description", ""),
            apply_url=raw.get("apply_url", ""),
            posted_at=posted_dt,
            posted_date=posted_dt,
            freshness_confidence=conf,
            freshness_source="linkedin",
            raw_data=raw,
        )
        gate = FreshnessGate()
        return gate.evaluate_job(job)

    async def fetch(self, source_id: str) -> Job:
        """Fetch single LinkedIn job detail."""
        url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{source_id}"
        async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return self.normalize({"source_id": source_id})
            soup = BeautifulSoup(resp.text, "html.parser")
            title_el = soup.find("h2", class_="top-card-layout__title")
            comp_el = soup.find("a", class_="topcard__org-name-link")
            desc_el = soup.find("div", class_="show-more-less-html__markup")
            return self.normalize({
                "source_id": source_id,
                "title": title_el.text.strip() if title_el else "Software Engineer",
                "company": comp_el.text.strip() if comp_el else "Unknown Company",
                "description": desc_el.text.strip() if desc_el else "",
                "apply_url": f"https://www.linkedin.com/jobs/view/{source_id}",
            })
