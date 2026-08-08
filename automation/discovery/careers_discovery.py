"""
automation/discovery/careers_discovery.py

Helios v5.0 Company Careers Discovery Engine.
Navigates official company career sites (e.g. jobs.siemens.com, careers.postman.com, cred.club/careers),
filters/searches relevant software/AI jobs, resolves canonical requisition keys, and ranks suitability.
"""
from typing import List, Optional
from automation.discovery.contracts import DiscoveredJob
from automation.verifier import get_canonical_requisition_key, load_processed_keys


COMPANY_CAREERS_PORTALS = {
    "siemens": "https://jobs.siemens.com/",
    "postman": "https://careers.postman.com/",
    "cred": "https://cred.club/careers",
    "razorpay": "https://razorpay.com/careers/"
}


class CareersDiscoveryEngine:
    @staticmethod
    async def discover_jobs(page, company: str, query: str = "Software Engineer") -> List[DiscoveredJob]:
        """
        Navigates official company careers page, searches target roles, and extracts active DiscoveredJob objects.
        Filters out previously applied canonical keys.
        """
        company_lower = company.lower()
        careers_url = COMPANY_CAREERS_PORTALS.get(company_lower, f"https://jobs.{company_lower}.com/")
        processed_keys = load_processed_keys()

        discovered: List[DiscoveredJob] = []
        try:
            await page.goto(careers_url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # Look for job search input
            search_input = await page.query_selector("input[type='search'], input[placeholder*='Search' i], input[data-automation-id='keywordSearchInput']")
            if search_input and await search_input.is_visible():
                await search_input.fill(query)
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(3000)

            # Query job link elements
            job_links = await page.query_selector_all("a[href*='job'], a[href*='careers'], a[data-automation-id='jobTitle']")
            for link in job_links[:10]:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if not href or len(text.strip()) < 3:
                    continue

                if not href.startswith("http"):
                    full_url = careers_url.rstrip("/") + "/" + href.lstrip("/")
                else:
                    full_url = href

                canon_key = get_canonical_requisition_key(full_url)
                if canon_key in processed_keys:
                    continue

                job = DiscoveredJob(
                    title=text.strip(),
                    company=company.title(),
                    location="India / Remote",
                    requisition_url=full_url,
                    canonical_key=canon_key,
                    match_score=0.95 if "engineer" in text.lower() or "developer" in text.lower() or "ai" in text.lower() else 0.80
                )
                discovered.append(job)

        except Exception as e:
            pass

        return discovered
