"""
automation/portals/strategies/base.py

Helios v5.0 Base ATS Strategy Contract.
All ATS strategies (Lever, Workday, Greenhouse, Generic) inherit from BaseStrategy,
produce standardized PageSchema contracts, and delegate execution to ActionExecutor.
"""
from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional
from automation.intelligence.page_understanding import PageUnderstandingEngine
from automation.intelligence.planner import ExecutionPlanner
from automation.intelligence.executor import ActionExecutor
from automation.intelligence.contracts import EvidencePayload, ExecutionPlan


class BaseStrategy(ABC):
    def __init__(self, ats_name: str, company_name: str = "generic"):
        self.ats_name = ats_name
        self.company_name = company_name
        self.page_engine = PageUnderstandingEngine()
        self.planner = ExecutionPlanner()
        self.executor = ActionExecutor()

    @abstractmethod
    async def prepare_page(self, page) -> None:
        """Navigates to application form /apply page if required."""
        pass

    async def execute_application(
        self,
        page,
        candidate_profile: Optional[Dict[str, Any]] = None,
        resume_pdf_path: Optional[str] = None
    ) -> Tuple[ExecutionPlan, EvidencePayload]:
        """
        Universal Application Lifecycle:
        1. Prepare page (/apply navigation)
        2. PageScan -> PageSchema
        3. ExecutionPlanner -> ExecutionPlan
        4. ActionExecutor -> EvidencePayload
        """
        await self.prepare_page(page)
        schema = await self.page_engine.analyze_page(page, ats_type=self.ats_name)
        
        if candidate_profile:
            self.planner = ExecutionPlanner(candidate_profile)

        plan = self.planner.create_plan(schema, resume_pdf_path=resume_pdf_path)
        evidence = await self.executor.execute_plan(page, plan)
        return (plan, evidence)
