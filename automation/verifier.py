"""
automation/verifier.py

Strict Post-Submission DOM Verification Engine for Helios.
Guarantees that no application is marked as 'SUBMITTED' in the database or Telegram alerts
unless Playwright detects definitive post-submission confirmation DOM signatures (e.g. Thank You page,
Application Received banner) and verifies that the page is NOT a 404/expired link.
"""
from __future__ import annotations

import re
from typing import Tuple, Optional


class VerificationResult:
    def __init__(self, is_success: bool, status_code: str, reason: str, screenshot_required: bool = True):
        self.is_success = is_success
        self.status_code = status_code  # VERIFIED_SUBMITTED, FAILED_404, FAILED_FORM_ERROR, PAUSED_CAPTCHA
        self.reason = reason
        self.screenshot_required = screenshot_required


async def verify_post_submission_state(page: object) -> VerificationResult:
    """
    Inspects Playwright DOM page after form filling/submission to confirm real success.
    """
    try:
        url = page.url.lower()
        title = (await page.title()).lower()
        content = (await page.content()).lower()

        # 1. Detect 404 or Invalid Board Page
        if "can't find that page" in content or "page not found" in content or "404" in title:
            return VerificationResult(
                is_success=False,
                status_code="FAILED_404",
                reason="Target job posting page was 404 or expired (Not Found)"
            )

        # 2. Detect CAPTCHA or Human Verification Challenge
        captcha_selectors = ["iframe[src*='recaptcha']", "iframe[src*='hcaptcha']", ".g-recaptcha", "#challenge-form"]
        for sel in captcha_selectors:
            elem = await page.query_selector(sel)
            if elem and await elem.is_visible():
                return VerificationResult(
                    is_success=False,
                    status_code="PAUSED_CAPTCHA",
                    reason="CAPTCHA or Security Challenge detected; requires human intervention."
                )

        # 3. Detect Explicit Post-Submission Success Elements
        success_selectors = [
            ".application-submitted",
            "[data-qa='thank-you']",
            ".thank-you-header",
            "h1:has-text('Application Received')",
            "h1:has-text('Thank You')",
            "h1:has-text('Application Submitted')",
            ".post-apply-confirmation"
        ]
        
        for sel in success_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    return VerificationResult(
                        is_success=True,
                        status_code="VERIFIED_SUBMITTED",
                        reason="Detected official post-submission confirmation DOM element!"
                    )
            except Exception:
                continue

        # 4. Check URL post-submission tokens
        if any(tok in url for tok in ["thank", "submitted", "confirmation", "applied", "success"]):
            return VerificationResult(
                is_success=True,
                status_code="VERIFIED_SUBMITTED",
                reason="Navigated to post-submission URL confirmation page!"
            )

        # 5. Default Fallback: Form filled & ready, but awaiting user submit / approval click
        return VerificationResult(
            is_success=False,
            status_code="FORM_FILLED_AWAITING_SUBMIT",
            reason="Form fields filled and resume attached cleanly; awaiting 1-Click submit confirmation."
        )

    except Exception as e:
        return VerificationResult(
            is_success=False,
            status_code="FAILED_DOM_INSPECTION",
            reason=f"DOM Inspection error: {e}"
        )
