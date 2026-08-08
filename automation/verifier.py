"""
automation/verifier.py

Helios Verification & Evidence Scoring Engine.
- JobFreshnessVerifier: Verifies HTTP status, job closure text, expiry, and deduplication before running application flows.
- EvidenceVerifier: Implements strict Evidence Scoring (STRONG vs WEAK) to enforce the GOLDEN RULE:
  Only STRONG evidence marks an application as CONFIRMED_APPLIED. WEAK evidence is marked SUBMISSION_UNVERIFIED and NOT counted as applied.
"""
import os
import json
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional

DEDUP_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "applied_urls_history.json")


@dataclass
class FreshnessResult:
    is_fresh: bool
    status_code: str
    reason: str


@dataclass
class EvidenceResult:
    status: str          # "CONFIRMED_APPLIED" vs "SUBMISSION_UNVERIFIED"
    score: str           # "STRONG" | "MEDIUM" | "WEAK"
    evidence_details: Dict[str, Any]


def load_processed_urls() -> set:
    if os.path.exists(DEDUP_FILE):
        try:
            with open(DEDUP_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


async def verify_job_freshness(page, apply_url: str) -> FreshnessResult:
    """Verifies if a job requisition URL is active, not 404, not closed, and not previously applied."""
    processed = load_processed_urls()
    if apply_url in processed:
        return FreshnessResult(is_fresh=False, status_code="DUPLICATE", reason="Requisition URL already in applied history")

    try:
        title = await page.title()
        title_lower = title.lower()

        # HTTP 404 Check
        if "404" in title_lower or "page not found" in title_lower or "not found" in title_lower:
            return FreshnessResult(is_fresh=False, status_code="FAILED_404", reason="Job Posting Link returned 404 Not Found")

        body_text = await page.inner_text("body")
        body_lower = body_text.lower()

        # Job Closed / Expired Keywords
        closed_keywords = [
            "job no longer available",
            "position has been filled",
            "no longer accepting applications",
            "requisition closed",
            "posting expired",
            "this job is closed"
        ]
        for kw in closed_keywords:
            if kw in body_lower:
                return FreshnessResult(is_fresh=False, status_code="CLOSED", reason=f"Job posting closed: '{kw}'")

        # Security CAPTCHA Check
        captcha_keywords = ["cloudflare", "captcha", "attention required", "security check"]
        for ckw in captcha_keywords:
            if ckw in title_lower or (ckw in body_lower and len(body_lower) < 500):
                return FreshnessResult(is_fresh=False, status_code="PAUSED_CAPTCHA", reason="Security CAPTCHA challenge detected")

        return FreshnessResult(is_fresh=True, status_code="ACTIVE", reason="Requisition active and verified fresh")

    except Exception as e:
        return FreshnessResult(is_fresh=False, status_code="ERROR", reason=f"Freshness check error: {e}")


async def verify_post_submission_evidence(page, application_id: Optional[str] = None) -> EvidenceResult:
    """Calculates Evidence Score to verify application submission."""
    evidence = {
        "dom_confirmation": False,
        "application_id": application_id,
        "portal_history": False,
        "email_confirmation": False,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    try:
        body_text = await page.inner_text("body")
        body_lower = body_text.lower()

        strong_dom_keywords = [
            "thank you for applying",
            "application submitted",
            "application received",
            "your application has been received",
            "we have received your application",
            "successfully submitted"
        ]

        for kw in strong_dom_keywords:
            if kw in body_lower:
                evidence["dom_confirmation"] = True
                break

        # Check URL for confirmation redirect
        url_lower = page.url.lower()
        is_medium_redirect = "thank" in url_lower or "confirm" in url_lower or "submitted" in url_lower

        if evidence["dom_confirmation"] or application_id:
            return EvidenceResult(
                status="CONFIRMED_APPLIED",
                score="STRONG",
                evidence_details=evidence
            )
        elif is_medium_redirect:
            return EvidenceResult(
                status="SUBMISSION_UNVERIFIED",
                score="MEDIUM",
                evidence_details=evidence
            )
        else:
            return EvidenceResult(
                status="SUBMISSION_UNVERIFIED",
                score="WEAK",
                evidence_details=evidence
            )

    except Exception as e:
        return EvidenceResult(
            status="SUBMISSION_UNVERIFIED",
            score="WEAK",
            evidence_details={"error": str(e)}
        )


# Backward compatibility helper for existing runners
async def verify_post_submission_state(page):
    f_res = await verify_job_freshness(page, page.url)
    if not f_res.is_fresh:
        class LegacyFreshnessResult:
            def __init__(self, code):
                self.status_code = code
                self.is_success = False
        return LegacyFreshnessResult(f_res.status_code)

    e_res = await verify_post_submission_evidence(page)
    class LegacyEvidenceResult:
        def __init__(self, is_succ):
            self.status_code = "SUBMITTED_VERIFIED" if is_succ else "FORM_FILLED_PREPARED"
            self.is_success = is_succ
    return LegacyEvidenceResult(e_res.status == "CONFIRMED_APPLIED")
