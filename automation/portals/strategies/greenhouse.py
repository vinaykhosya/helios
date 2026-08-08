"""
automation/portals/strategies/greenhouse.py

Helios v5.0 Greenhouse ATS Strategy.
Inherits from BaseStrategy, resolves Greenhouse-specific input selectors (#first_name, #last_name, #email, #phone, #resume_file_input),
and delegates to Universal Page Understanding and Action Executor.
"""
from automation.portals.strategies.base import BaseStrategy


class GreenhouseStrategy(BaseStrategy):
    def __init__(self, company_name: str = "generic"):
        super().__init__(ats_name="greenhouse", company_name=company_name)

    async def prepare_page(self, page) -> None:
        """
        Greenhouse job boards (boards.greenhouse.io or job-boards.greenhouse.io) embed the application form directly on the page.
        Scrolls form into view if needed.
        """
        try:
            form_elem = await page.query_selector("form#application_form, #application")
            if form_elem:
                await form_elem.scroll_into_view_if_needed()
        except Exception:
            pass
