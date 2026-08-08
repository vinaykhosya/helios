"""
automation/portals/strategies/generic.py

Helios v5.0 Generic Universal Strategy.
Handles unknown or custom company portals using PageUnderstandingEngine & Semantic Mapping.
"""
from automation.portals.strategies.base import BaseStrategy


class GenericStrategy(BaseStrategy):
    def __init__(self, company_name: str = "generic"):
        super().__init__(ats_name="generic", company_name=company_name)

    async def prepare_page(self, page) -> None:
        """
        Generic strategy evaluates current page directly.
        """
        pass
