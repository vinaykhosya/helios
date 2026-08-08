"""
automation/portals/strategies/workday.py

Helios v5.0 Workday ATS Strategy.
Inherits from BaseStrategy, handles Workday enterprise portals (myworkdayjobs.com),
maps data-automation-id attributes, multi-step navigation buttons, and session authentication.
"""
from automation.portals.strategies.base import BaseStrategy


class WorkdayStrategy(BaseStrategy):
    def __init__(self, company_name: str = "generic"):
        super().__init__(ats_name="workday", company_name=company_name)

    async def prepare_page(self, page) -> None:
        """
        Workday career portals require clicking 'Apply' or 'Apply Manually' if on job description page.
        """
        try:
            apply_btn = await page.query_selector("a[data-automation-id='applyButton'], button[data-automation-id='applyButton']")
            if apply_btn and await apply_btn.is_visible():
                await apply_btn.click()
                await page.wait_for_timeout(2000)
        except Exception:
            pass
