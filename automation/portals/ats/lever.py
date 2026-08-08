"""
automation/portals/ats/lever.py

Lever ATS Portal Adapter for Helios v4.0.
- Handles Lever requisition navigation (/apply page redirection).
- Fills form inputs, attaches resume, and submits application.
- Generates forensic execution records (url_before, url_after, confirmation_detected).
"""
import time
from typing import Dict, Any, Tuple
from automation.portals.base import PortalAdapter, AuthState


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
        return True

    async def search_requisitions(self, page, query: str, location: str = "India") -> list:
        return []

    async def fill_requisition_form(self, page, candidate_profile: dict, resume_pdf_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Executes Lever form filling & submission flow.
        Returns: (success_bool, forensic_record_dict)
        """
        forensic = {
            "ats_type": "lever",
            "url_before": page.url,
            "page_title_before": await page.title(),
            "apply_button_clicked": False,
            "fields_filled": 0,
            "resume_attached": False,
            "submit_button_found": False,
            "submit_button_clicked": False,
            "url_after": None,
            "page_title_after": None,
            "confirmation_detected": False
        }

        try:
            # 1. Check if we need to click "Apply for this job" or append /apply
            url_lower = page.url.lower()
            if not url_lower.endswith("/apply") and not "/apply?" in url_lower:
                apply_link = await page.query_selector("a:has-text('Apply for this job'), a.postings-btn")
                if apply_link and await apply_link.is_visible():
                    await apply_link.click()
                    await page.wait_for_timeout(1500)
                    forensic["apply_button_clicked"] = True
                elif not "/apply" in page.url:
                    target_apply_url = page.url.rstrip("/") + "/apply"
                    await page.goto(target_apply_url, timeout=10000, wait_until="domcontentloaded")

            # 2. Fill Form Fields
            n1 = await self._fill_field(page, ["#first_name", "input[name*='name']", "input[name='name']", "#name"], candidate_profile.get("name", "Vinay Khosya"))
            e1 = await self._fill_field(page, ["#email", "input[name*='email']"], candidate_profile.get("email", "vinay.khosya.ug23@nsut.ac.in"))
            p1 = await self._fill_field(page, ["#phone", "input[name*='phone']"], candidate_profile.get("phone", "+919996303072"))
            o1 = await self._fill_field(page, ["#org", "input[name*='org']", "input[name*='company']"], candidate_profile.get("org", "NSUT Delhi"))
            l1 = await self._fill_field(page, ["#urls\\[LinkedIn\\]", "input[name*='linkedin']"], candidate_profile.get("linkedin", "https://linkedin.com/in/vinaykhosya"))
            g1 = await self._fill_field(page, ["#urls\\[GitHub\\]", "input[name*='github']"], candidate_profile.get("github", "https://github.com/vinaykhosya"))

            forensic["fields_filled"] = sum([n1, e1, p1, o1, l1, g1])

            # 3. File Upload
            file_inputs = await page.query_selector_all("input[type='file']")
            if file_inputs:
                try:
                    await file_inputs[0].set_input_files(resume_pdf_path)
                    forensic["resume_attached"] = True
                except Exception:
                    pass

            # 4. Submit Button
            submit_btn = await page.query_selector("button[type='submit'], input[type='submit'], #btn-submit, .template-btn-submit, button:has-text('Submit application')")
            if submit_btn and await submit_btn.is_visible():
                forensic["submit_button_found"] = True
                await submit_btn.click()
                await page.wait_for_timeout(3000)
                forensic["submit_button_clicked"] = True

            forensic["url_after"] = page.url
            forensic["page_title_after"] = await page.title()

            # Check Confirmation
            after_url = page.url.lower()
            body_text = (await page.inner_text("body")).lower()
            if "/thanks" in after_url or "thanks for applying" in body_text or "application submitted" in body_text or "received your application" in body_text:
                forensic["confirmation_detected"] = True

            return (forensic["fields_filled"] > 0, forensic)

        except Exception as e:
            forensic["error"] = str(e)
            return (False, forensic)

    async def _fill_field(self, page, selectors, value) -> bool:
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem and await elem.is_visible():
                    await page.fill(sel, value)
                    return True
            except Exception:
                continue
        return False
