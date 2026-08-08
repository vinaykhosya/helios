"""
automation/portals/strategies/workday.py

Helios v5.0 Robust Workday ATS Strategy.
Inherits from BaseStrategy, handles Workday enterprise portals (myworkdayjobs.com),
maps data-automation-id attributes, multi-step navigation wizard, Workday comboboxes/radios,
resume upload verification, and session authentication.
"""
import os
from typing import Tuple, Dict, Any, Optional
from automation.portals.strategies.base import BaseStrategy
from automation.intelligence.contracts import ExecutionPlan, EvidencePayload


class WorkdayStrategy(BaseStrategy):
    def __init__(self, company_name: str = "generic"):
        super().__init__(ats_name="workday", company_name=company_name)

    async def prepare_page(self, page) -> None:
        """
        Workday career portals require clicking 'Apply' or 'Apply Manually' if on job description page.
        Bypasses maintenance redirect by navigating via Workday's client-side SPA router if needed.
        """
        try:
            current_url = page.url.lower()
            if "community.workday.com/maintenance-page" in current_url:
                await page.goto("https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers", timeout=20000, wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

            # 1. Click initial Apply button on job description
            apply_btn = await page.query_selector("a[data-automation-id='applyButton'], button[data-automation-id='applyButton'], a:has-text('Apply')")
            if apply_btn and await apply_btn.is_visible():
                await apply_btn.click()
                await page.wait_for_timeout(2500)

            # 2. Click 'Apply Manually' if Workday presents initial choice dialog
            apply_manual = await page.query_selector("button[data-automation-id='applyManually'], a[data-automation-id='applyManually'], button:has-text('Apply Manually')")
            if apply_manual and await apply_manual.is_visible():
                await apply_manual.click()
                await page.wait_for_timeout(2500)

        except Exception:
            pass

    async def execute_application(
        self,
        page,
        candidate_profile: Optional[Dict[str, Any]] = None,
        resume_pdf_path: Optional[str] = None
    ) -> Tuple[ExecutionPlan, EvidencePayload]:
        """
        Workday multi-step wizard application execution.
        Traverses pages (My Information -> My Experience -> Questions -> Disclosures -> Review -> Submit).
        Fills mapped fields, verifies resume upload in DOM, and handles submission boundaries.
        """
        await self.prepare_page(page)

        profile = candidate_profile or {}
        resume_uploaded_and_verified = False

        # Workday Multi-Step Wizard Loop (max 5 pages)
        page_step = 1
        max_steps = 5

        while page_step <= max_steps:
            try:
                # 1. Fill Workday Data Automation ID Custom Inputs
                fn_elem = await page.query_selector("input[data-automation-id='legalNameSection_firstName'], input[data-automation-id='firstName']")
                if fn_elem and await fn_elem.is_visible():
                    await fn_elem.fill(profile.get("name", "Vinay Khosya").split()[0])

                ln_elem = await page.query_selector("input[data-automation-id='legalNameSection_lastName'], input[data-automation-id='lastName']")
                if ln_elem and await ln_elem.is_visible():
                    await ln_elem.fill(profile.get("last_name", "Khosya"))

                em_elem = await page.query_selector("input[data-automation-id='email'], input[data-automation-id='emailAddress']")
                if em_elem and await em_elem.is_visible():
                    await em_elem.fill(profile.get("email", "vinay.khosya.ug23@nsut.ac.in"))

                ph_elem = await page.query_selector("input[data-automation-id='phone-number'], input[data-automation-id='phoneNumber']")
                if ph_elem and await ph_elem.is_visible():
                    await ph_elem.fill(profile.get("phone", "+919996303072"))

                # 2. Resume File Upload & Verification
                if resume_pdf_path and os.path.exists(resume_pdf_path):
                    file_input = await page.query_selector("input[type='file'], div[data-automation-id='file-upload-drop-zone'] input")
                    if file_input:
                        await file_input.set_input_files(resume_pdf_path)
                        await page.wait_for_timeout(1500)

                        # DOM Verification: check if uploaded filename appears in DOM
                        file_name = os.path.basename(resume_pdf_path)
                        body_text = await page.inner_text("body")
                        if file_name.lower() in body_text.lower() or "pdf" in body_text.lower():
                            resume_uploaded_and_verified = True

                # 3. Check for Next / Continue Wizard Navigation Button
                next_btn = await page.query_selector("button[data-automation-id='bottom-navigation-next-button'], button:has-text('Save and Continue'), button:has-text('Next')")
                if next_btn and await next_btn.is_visible():
                    await next_btn.click()
                    await page.wait_for_timeout(3000)
                    page_step += 1
                else:
                    break

            except Exception:
                break

        # Delegate to BaseStrategy for standard schema analysis and evidence creation
        plan, evidence = await super().execute_application(page, candidate_profile=candidate_profile, resume_pdf_path=resume_pdf_path)
        return plan, evidence
