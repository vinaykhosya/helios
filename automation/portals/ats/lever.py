"""
automation/portals/ats/lever.py

Lever ATS Portal Adapter for Helios v4.0.
"""
from typing import Dict, Any, Optional
from automation.portals.base import PortalAdapter, AuthState
from automation.verifier import verify_post_submission_evidence


class LeverAdapter(PortalAdapter):
    def __init__(self, company_name: str = "generic"):
        super().__init__(portal_name=company_name, ats_type="lever")

    async def detect_auth_state(self, page) -> AuthState:
        try:
            body = await page.inner_text("body")
            if "cloudflare" in body.lower() or "captcha" in body.lower():
                return AuthState.CAPTCHA_REQUIRED
            return AuthState.AUTHENTICATED
        except Exception:
            return AuthState.UNKNOWN

    async def perform_login(self, page, credentials: Dict[str, str]) -> bool:
        # Lever postings are direct public forms unless internal candidate portal is specified
        return True

    async def search_requisitions(self, page, query: str, location: str = "India") -> list:
        # Lever list parsing
        return []

    async def fill_requisition_form(self, page, candidate_profile: dict, resume_pdf_path: str) -> bool:
        """Executes multi-step or single-step form filling on Lever application form."""
        try:
            # 1. Fill Text Inputs
            await self._fill_field(page, ["#first_name", "input[name*='name']", "#name"], candidate_profile.get("name", "Vinay Khosya"))
            await self._fill_field(page, ["#email", "input[name*='email']"], candidate_profile.get("email", "vinay.khosya.ug23@nsut.ac.in"))
            await self._fill_field(page, ["#phone", "input[name*='phone']"], candidate_profile.get("phone", "+919996303072"))
            await self._fill_field(page, ["#org", "input[name*='org']", "input[name*='company']"], candidate_profile.get("org", "NSUT Delhi"))
            await self._fill_field(page, ["#urls\\[LinkedIn\\]", "input[name*='linkedin']"], candidate_profile.get("linkedin", "https://linkedin.com/in/vinaykhosya"))
            await self._fill_field(page, ["#urls\\[GitHub\\]", "input[name*='github']"], candidate_profile.get("github", "https://github.com/vinaykhosya"))

            # 2. File Upload
            file_inputs = await page.query_selector_all("input[type='file']")
            if file_inputs:
                try:
                    await file_inputs[0].set_input_files(resume_pdf_path)
                except Exception:
                    pass

            # 3. Submit Button Click
            submit_btn = await page.query_selector("button[type='submit'], input[type='submit'], #btn-submit, .template-btn-submit")
            if submit_btn:
                await submit_btn.click()
                await page.wait_for_timeout(2000)
                return True

            return False
        except Exception:
            return False

    async def _fill_field(self, page, selectors, value):
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    await page.fill(sel, value)
                    return True
            except Exception:
                continue
        return False
