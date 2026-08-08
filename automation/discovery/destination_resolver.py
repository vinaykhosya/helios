"""
automation/discovery/destination_resolver.py

Helios v5.0 Apply Destination Resolver.
Resolves the real application destination from a DiscoveredJob by navigating the job detail page,
identifying the actual Apply / Apply Now / Apply Manually control, capturing the redirect chain,
and verifying whether the destination is a valid application portal.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class DestinationResolution:
    resolved: bool
    initial_url: str
    final_url: str
    redirect_chain: List[str] = field(default_factory=list)
    apply_control_found: bool = False
    apply_control_selector: Optional[str] = None
    is_valid_application_flow: bool = False
    is_maintenance: bool = False
    error_reason: Optional[str] = None


class ApplyDestinationResolver:
    @staticmethod
    async def resolve_destination(page, job_url: str) -> DestinationResolution:
        """
        Navigates the real job detail page, identifies Apply controls, clicks or extracts hrefs,
        tracks redirect chains, and returns DestinationResolution.
        """
        redirect_chain: List[str] = [job_url]
        resolution = DestinationResolution(
            resolved=False,
            initial_url=job_url,
            final_url=job_url,
            redirect_chain=redirect_chain
        )

        try:
            # 1. Navigate Job Detail Page
            response = await page.goto(job_url, timeout=25000, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            current_url = page.url
            if current_url != job_url:
                redirect_chain.append(current_url)

            # Check for immediate maintenance redirect
            if "community.workday.com/maintenance-page" in current_url.lower() or "unavailable" in (await page.title()).lower():
                resolution.final_url = current_url
                resolution.is_maintenance = True
                resolution.error_reason = "WORKDAY_MAINTENANCE_REDIRECT"
                return resolution

            # 2. Search for Apply controls in DOM
            apply_selectors = [
                "a[data-automation-id='applyButton']",
                "button[data-automation-id='applyButton']",
                "a[href*='apply']",
                "button:has-text('Apply')",
                "a:has-text('Apply')",
                "button:has-text('Apply Now')",
                "a:has-text('Apply Now')"
            ]

            apply_elem = None
            found_selector = None
            for sel in apply_selectors:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    apply_elem = elem
                    found_selector = sel
                    break

            if apply_elem:
                resolution.apply_control_found = True
                resolution.apply_control_selector = found_selector

                href = await apply_elem.get_attribute("href")
                if href and href.startswith("http") and href != job_url:
                    await page.goto(href, timeout=20000, wait_until="domcontentloaded")
                else:
                    await apply_elem.click()
                    await page.wait_for_timeout(3000)

                post_apply_url = page.url
                if post_apply_url not in redirect_chain:
                    redirect_chain.append(post_apply_url)

                resolution.final_url = post_apply_url

                # Check if choice button exists (e.g. Apply Manually)
                manual_btn = await page.query_selector("button[data-automation-id='applyManually'], a[data-automation-id='applyManually'], button:has-text('Apply Manually')")
                if manual_btn and await manual_btn.is_visible():
                    await manual_btn.click()
                    await page.wait_for_timeout(3000)
                    if page.url not in redirect_chain:
                        redirect_chain.append(page.url)
                    resolution.final_url = page.url

            # 3. Validate Destination Portal State
            final_lower = resolution.final_url.lower()
            page_title = (await page.title()).lower()

            if "community.workday.com/maintenance-page" in final_lower or "unavailable" in page_title:
                resolution.is_maintenance = True
                resolution.error_reason = "WORKDAY_MAINTENANCE_REDIRECT"
            elif "404" in page_title or "not found" in page_title:
                resolution.error_reason = "HTTP_404_NOT_FOUND"
            else:
                resolution.resolved = True
                resolution.is_valid_application_flow = True

        except Exception as e:
            resolution.error_reason = str(e)

        return resolution
