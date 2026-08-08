"""
automation/intelligence/page_understanding.py

Helios v5.0 Page Understanding Engine.
Scans Playwright pages and produces the standardized PageSchema central contract.
"""
from typing import Optional, List
from automation.intelligence.contracts import (
    PageSchema,
    PageType,
    DetectedElement,
    ElementSemantic
)
from automation.intelligence.selectors import SelectorResolver

TARGET_SEMANTICS = [
    ElementSemantic.FIRST_NAME,
    ElementSemantic.LAST_NAME,
    ElementSemantic.EMAIL,
    ElementSemantic.PHONE,
    ElementSemantic.ORGANIZATION,
    ElementSemantic.LINKEDIN,
    ElementSemantic.GITHUB
]


class PageUnderstandingEngine:
    async def analyze_page(self, page, ats_type: str = "generic") -> PageSchema:
        """
        Scans DOM and constructs standardized PageSchema contract.
        """
        url_lower = page.url.lower()
        title_lower = (await page.title()).lower()
        body_text = (await page.inner_text("body")).lower()

        # 1. Detect PageType
        page_type = PageType.APPLICATION_FORM
        has_captcha = False
        has_login = False

        if "cloudflare" in body_text or "captcha" in body_text or "security check" in title_lower:
            page_type = PageType.CAPTCHA_CHALLENGE
            has_captcha = True
        elif "/thanks" in url_lower or "thanks for applying" in body_text or "application submitted" in body_text:
            page_type = PageType.THANK_YOU_CONFIRMATION
        elif "sign in" in body_text and "password" in body_text and len(body_text) < 1000:
            page_type = PageType.LOGIN_REQUIRED
            has_login = True

        detected_fields: List[DetectedElement] = []
        detected_buttons: List[DetectedElement] = []

        # 2. Scan Form Input Fields via SelectorResolver
        if page_type == PageType.APPLICATION_FORM:
            for sem in TARGET_SEMANTICS:
                loc = await SelectorResolver.locate_element(page, sem)
                if loc:
                    elem_handle, selector_str, conf = loc
                    detected_fields.append(
                        DetectedElement(
                            element_id=f"elem-{sem.value}",
                            selector_used=selector_str,
                            tag_name="input",
                            element_type="text",
                            semantic=sem,
                            confidence=conf
                        )
                    )

            # 3. Detect Submit Button
            submit_btn = await page.query_selector("button[type='submit'], input[type='submit'], #btn-submit, .template-btn-submit")
            if submit_btn and await submit_btn.is_visible():
                detected_buttons.append(
                    DetectedElement(
                        element_id="btn-submit",
                        selector_used="button[type='submit']",
                        tag_name="button",
                        element_type="submit",
                        semantic=ElementSemantic.SUBMIT_APPLICATION,
                        confidence=0.99
                    )
                )

        return PageSchema(
            page_type=page_type,
            ats_type=ats_type,
            fields=detected_fields,
            buttons=detected_buttons,
            has_captcha=has_captcha,
            has_login_prompt=has_login
        )
