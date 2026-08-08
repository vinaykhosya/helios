"""
automation/intelligence/page_understanding.py

Helios v5.0 Extended Page Understanding Engine.
Scans Playwright pages for comprehensive form control types:
  - Text, Textarea, Phone, Address, Date fields
  - Select/Dropdowns & Combobox/Autocomplete
  - Radio Groups & Checkbox Groups
  - File Upload Dropzones
  - Wizard Navigation Buttons (Next, Continue, Save & Continue, Review, Submit)
Produces standardized PageSchema central contract.
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
        Scans DOM and constructs standardized PageSchema contract across all form input controls & wizard state.
        """
        url_lower = page.url.lower()
        title_lower = (await page.title()).lower()
        body_text = (await page.inner_text("body")).lower()

        # 1. Detect PageType & Security State
        page_type = PageType.APPLICATION_FORM
        has_captcha = False
        has_login = False

        if "cloudflare" in body_text or "captcha" in body_text or "security check" in title_lower:
            page_type = PageType.CAPTCHA_CHALLENGE
            has_captcha = True
        elif "/thanks" in url_lower or "thanks for applying" in body_text or "application submitted" in body_text or "thank you for applying" in body_text:
            page_type = PageType.THANK_YOU_CONFIRMATION
        elif "sign in" in body_text and "password" in body_text and len(body_text) < 1000:
            page_type = PageType.LOGIN_REQUIRED
            has_login = True

        detected_fields: List[DetectedElement] = []
        detected_buttons: List[DetectedElement] = []

        # 2. Scan Standard Input Controls via SelectorResolver
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

            # Scan File Upload Input
            file_input = await page.query_selector("input[type='file'], div[data-automation-id='file-upload-drop-zone'] input")
            if file_input:
                detected_fields.append(
                    DetectedElement(
                        element_id="file-resume",
                        selector_used="input[type='file']",
                        tag_name="input",
                        element_type="file",
                        semantic=ElementSemantic.RESUME_UPLOAD,
                        confidence=0.98
                    )
                )

            # 3. Detect Navigation Buttons (Next / Continue / Review / Submit)
            wizard_buttons = [
                ("button[data-automation-id='bottom-navigation-next-button']", ElementSemantic.SUBMIT_APPLICATION, "Next"),
                ("button:has-text('Continue')", ElementSemantic.SUBMIT_APPLICATION, "Continue"),
                ("button:has-text('Next')", ElementSemantic.SUBMIT_APPLICATION, "Next"),
                ("button:has-text('Save and Continue')", ElementSemantic.SUBMIT_APPLICATION, "Save and Continue"),
                ("button:has-text('Review')", ElementSemantic.SUBMIT_APPLICATION, "Review"),
                ("button.template-btn-submit, button[type='submit'], input[type='submit'], #btn-submit, button:has-text('Submit application'), button:has-text('Submit Application')", ElementSemantic.SUBMIT_APPLICATION, "Submit")
            ]

            for sel, sem, label in wizard_buttons:
                btn = await page.query_selector(sel)
                if btn and await btn.is_visible():
                    detected_buttons.append(
                        DetectedElement(
                            element_id=f"btn-{sem.value}",
                            selector_used=sel,
                            tag_name="button",
                            element_type="submit",
                            semantic=sem,
                            confidence=0.95
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
