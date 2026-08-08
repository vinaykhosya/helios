"""
automation/verifier.py

Helios Verification & Evidence Scoring Engine v4.0.
- JobFreshnessVerifier: Checks HTTP status, job closure text, expiry, and Canonical Application Key deduplication before running application flows.
- EvidenceVerifier: Implements strict Evidence Scoring (STRONG vs WEAK) to enforce the GOLDEN RULE:
  An application is ONLY marked CONFIRMED_APPLIED if submit_clicked IS TRUE, page state transitioned, and live portal confirmation DOM/ID is verified.
"""
import os
import json
import time
import urllib.parse
import re
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


def get_canonical_requisition_key(url: str) -> str:
    """
    Extracts canonical key (portal:company:requisition_id) from URL.
    Strips query parameters like ?source=linkedin or ?source=indeed.
    """
    parsed = urllib.parse.urlparse(url)
    clean_path = parsed.path.rstrip("/").lower()
    
    # Handle Lever URLs (e.g. /company/requisition_id/apply -> company:requisition_id)
    if "lever.co" in parsed.netloc:
        parts = [p for p in clean_path.split("/") if p and p != "apply" and p != "thanks"]
        if len(parts) >= 2:
            return f"lever:{parts[0]}:{parts[1]}"

    # Handle Greenhouse URLs
    elif "greenhouse.io" in parsed.netloc:
        parts = [p for p in clean_path.split("/") if p and p != "apply"]
        if len(parts) >= 2:
            return f"greenhouse:{parts[0]}:{parts[-1]}"

    # Handle Workday URLs (e.g. siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers/job/Bangalore-India/Software-Engineer_R105492)
    elif "myworkdayjobs.com" in parsed.netloc:
        company = parsed.netloc.split(".")[0]
        parts = [p for p in clean_path.split("/") if p and p not in ["en-us", "job"]]
        if len(parts) >= 1:
            req_slug = parts[-1]
            return f"workday:{company}:{req_slug}"
        return f"workday:{company}:main"
    
    # Fallback to normalized base URL without query params
    return f"url:{parsed.netloc}{clean_path}"


def load_processed_keys() -> set:
    if os.path.exists(DEDUP_FILE):
        try:
            with open(DEDUP_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                keys = set()
                for item in data:
                    if item.startswith("lever:") or item.startswith("greenhouse:") or item.startswith("workday:") or item.startswith("url:"):
                        keys.add(item)
                    else:
                        keys.add(get_canonical_requisition_key(item))
                return keys
        except Exception:
            pass
    return set()


def save_processed_key(url: str):
    processed = load_processed_keys()
    canon_key = get_canonical_requisition_key(url)
    processed.add(canon_key)
    try:
        os.makedirs(os.path.dirname(DEDUP_FILE), exist_ok=True)
        with open(DEDUP_FILE, "w", encoding="utf-8") as f:
            json.dump(list(processed), f, indent=2)
    except Exception:
        pass


async def verify_job_freshness(page, apply_url: str) -> FreshnessResult:
    """Verifies if a job requisition URL is active, not 404, not closed, and not previously applied."""
    canon_key = get_canonical_requisition_key(apply_url)
    processed = load_processed_keys()
    
    if canon_key in processed:
        return FreshnessResult(is_fresh=False, status_code="DUPLICATE", reason=f"Canonical key '{canon_key}' already in applied history")

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


async def verify_post_submission_evidence(
    page,
    submit_clicked: bool = False,
    live_application_id: Optional[str] = None,
    application_id_source: str = "NONE"
) -> EvidenceResult:
    """
    Calculates Evidence Score to verify application submission.
    GOLDEN RULE: If submit_clicked is False, NEVER mark as CONFIRMED_APPLIED.
    Application ID is ONLY evidence if source is 'LIVE_PORTAL_DOM'.
    """
    evidence = {
        "submit_clicked": submit_clicked,
        "dom_confirmation": False,
        "application_id": live_application_id if application_id_source == "LIVE_PORTAL_DOM" else None,
        "application_id_source": application_id_source if live_application_id else "NONE",
        "portal_history": False,
        "email_confirmation": False,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

    # Strict Integrity Rule: Must have clicked submit!
    if not submit_clicked:
        return EvidenceResult(
            status="SUBMISSION_UNVERIFIED",
            score="WEAK",
            evidence_details=evidence
        )

    try:
        body_text = await page.inner_text("body")
        body_lower = body_text.lower()

        strong_dom_keywords = [
            "thank you for applying",
            "thanks for applying",
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

        url_lower = page.url.lower()
        is_thanks_redirect = "/thanks" in url_lower or "confirm" in url_lower or "submitted" in url_lower

        if (evidence["dom_confirmation"] or is_thanks_redirect) and evidence["application_id"]:
            return EvidenceResult(
                status="CONFIRMED_APPLIED",
                score="STRONG",
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
