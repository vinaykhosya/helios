"""
automation/discovery/careers_discovery.py

Helios v5.0 Company Careers Discovery Engine.
Navigates official company career sites (e.g. jobs.siemens.com, careers.postman.com, cred.club/careers),
filters out non-job navigation links, verifies job detail pages, resolves canonical requisition keys, and ranks suitability.
"""
import re
from typing import List, Optional
from automation.discovery.contracts import DiscoveredJob
from automation.verifier import get_canonical_requisition_key, load_processed_keys


COMPANY_CAREERS_PORTALS = {
    "siemens": "https://jobs.siemens.com/en_US/externaljobs/SearchJobs",
    "postman": "https://careers.postman.com/",
    "cred": "https://cred.club/careers",
    "razorpay": "https://razorpay.com/careers/"
}

# Non-job navigation/utility keywords to strictly reject
NAVIGATION_REJECT_KEYWORDS = [
    "/home", "/searchjobs", "/airecommendations", "faq.html",
    "/de_de/", "/fr_fr/", "/es_es/", "/nl_nl/", "language",
    "privacy", "terms", "about-us", "cookies", "login", "register"
]


class CareersDiscoveryEngine:
    @staticmethod
    async def discover_jobs(page, company: str, query: str = "Software Engineer") -> List[DiscoveredJob]:
        """
        Navigates official company careers page, searches target roles, and extracts verified DiscoveredJob objects.
        Filters out non-job navigation links and previously applied canonical keys.
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
            job_links = await page.query_selector_all("a[href*='job'], a[href*='Siemens_Careers'], a[data-automation-id='jobTitle']")
            for link in job_links[:15]:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if not href or len(text.strip()) < 3:
                    continue

                href_lower = href.lower()

                # Reject navigation, search index, or language links
                if any(nav_kw in href_lower for nav_kw in NAVIGATION_REJECT_KEYWORDS):
                    continue

                # Verify if link represents an actual job detail page
                is_job_page = bool(
                    "/job/" in href_lower
                    or "/jobs/" in href_lower
                    or "siemens_careers/job/" in href_lower
                    or re.search(r'_[a-z0-9]+$', href_lower)
                )

                if not is_job_page:
                    continue

                if not href.startswith("http"):
                    full_url = careers_url.rstrip("/") + "/" + href.lstrip("/")
                else:
                    full_url = href

                canon_key = get_canonical_requisition_key(full_url)
                if canon_key in processed_keys:
                    continue

                # Parse requisition ID
                req_match = re.search(r'[_/]([A-Z0-9]{5,15})$', full_url, re.IGNORECASE)
                req_id = req_match.group(1) if req_match else None

                # Detect application system
                if "workday" in full_url or "myworkdayjobs" in full_url:
                    ats = "WORKDAY"
                elif "greenhouse.io" in full_url:
                    ats = "GREENHOUSE"
                elif "lever.co" in full_url:
                    ats = "LEVER"
                else:
                    ats = "GENERIC"

                job = DiscoveredJob(
                    title=text.strip(),
                    company=company.title(),
                    location="India / Remote",
                    requisition_url=full_url,
                    canonical_key=canon_key,
                    match_score=0.94 if "engineer" in text.lower() or "developer" in text.lower() or "ai" in text.lower() else 0.80,
                    application_url=full_url,
                    application_system=ats,
                    requisition_id=req_id,
                    is_job_detail_page=True
                )
                discovered.append(job)

        except Exception as e:
            pass

        return discovered
