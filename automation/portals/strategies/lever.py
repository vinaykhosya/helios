"""
automation/portals/strategies/lever.py

Helios v5.0 Lever ATS Strategy.
Inherits from BaseStrategy, handles /apply page navigation, and delegates to Universal Engine.
"""
from automation.portals.strategies.base import BaseStrategy


class LeverStrategy(BaseStrategy):
    def __init__(self, company_name: str = "generic"):
        super().__init__(ats_name="lever", company_name=company_name)

    async def prepare_page(self, page) -> None:
        """Navigates to Lever /apply URL if currently on description page."""
        url_lower = page.url.lower()
        if not url_lower.endswith("/apply") and not "/apply?" in url_lower:
            apply_link = await page.query_selector("a:has-text('Apply for this job'), a.postings-btn")
            if apply_link and await apply_link.is_visible():
                await apply_link.click()
                await page.wait_for_timeout(1500)
            elif not "/apply" in url_lower:
                target_apply_url = page.url.rstrip("/") + "/apply"
                await page.goto(target_apply_url, timeout=10000, wait_until="domcontentloaded")
