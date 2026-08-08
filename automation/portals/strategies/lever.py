"""
automation/portals/strategies/lever.py

Helios v5.0 Lever ATS Strategy.
Inherits from BaseStrategy, handles /apply page navigation,
handles asynchronous resume parsing states ("Analyzing resume..."),
and delegates to Universal Engine.
"""
import time
from typing import Tuple, Dict, Any, Optional
from automation.portals.strategies.base import BaseStrategy
from automation.intelligence.planner import ExecutionPlanner
from automation.intelligence.contracts import ExecutionPlan, EvidencePayload


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

    async def wait_for_resume_processing(self, page, timeout_sec: int = 30) -> bool:
        """
        Waits for Lever asynchronous resume parsing indicators ("Analyzing resume...", "Uploading...") to disappear.
        Returns True if processing completes cleanly before timeout.
        """
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            try:
                body_text = await page.inner_text("body")
                body_lower = body_text.lower()

                processing_keywords = ["analyzing resume", "uploading...", "processing...", "parsing resume"]
                is_processing = any(kw in body_lower for kw in processing_keywords)

                if is_processing:
                    await page.wait_for_timeout(1500)
                else:
                    return True
            except Exception:
                break
        return False

    async def execute_application(
        self,
        page,
        candidate_profile: Optional[Dict[str, Any]] = None,
        resume_pdf_path: Optional[str] = None
    ) -> Tuple[ExecutionPlan, EvidencePayload]:
        """
        Overridden execute_application for Lever:
        1. Prepare page (/apply navigation)
        2. Initial PageScan & ExecutionPlan
        3. ActionExecutor fills fields & attaches resume file
        4. Invokes wait_for_resume_processing to wait for 'Analyzing resume...' to complete & reach 'Success!'
        5. Re-analyzes page DOM & clicks Submit if enabled in LIVE mode.
        """
        await self.prepare_page(page)
        schema = await self.page_engine.analyze_page(page, ats_type=self.ats_name)

        if candidate_profile:
            self.planner = ExecutionPlanner(candidate_profile)

        plan = self.planner.create_plan(schema, resume_pdf_path=resume_pdf_path)
        evidence = await self.executor.execute_plan(page, plan)

        # Wait for resume parsing if resume was attached
        if resume_pdf_path:
            await self.wait_for_resume_processing(page, timeout_sec=30)
            
            # Re-scan page to ensure submit button enabled state is fresh
            updated_schema = await self.page_engine.analyze_page(page, ats_type=self.ats_name)
            plan = self.planner.create_plan(updated_schema, resume_pdf_path=resume_pdf_path)
            
            if self.executor.mode == "live" and plan.submission_allowed:
                evidence = await self.executor.execute_plan(page, plan)

        return (plan, evidence)
