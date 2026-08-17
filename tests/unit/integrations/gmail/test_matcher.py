"""
tests/unit/integrations/gmail/test_matcher.py

Unit tests for EmailApplicationMatcher 5-level matching hierarchy with Level 1 token and Level 3 ambiguity safety.
"""
import pytest
from integrations.gmail.matcher import EmailApplicationMatcher, MatchConfidence


def make_apps(*companies):
    return [
        {
            "id": f"app-{c}",
            "company_domain": f"{c.lower()}.com",
            "company_name": c,
            "job_title": "Software Engineer",
            "apply_url": f"https://jobs.{c.lower()}.com/123",
            "status": "saved",
        }
        for c in companies
    ]


def test_no_apps_no_match():
    m = EmailApplicationMatcher()
    r = m.match("hr@google.com", "google.com", "Update", "", [])
    assert r.confidence == MatchConfidence.NO_MATCH
    assert r.application_id is None
    assert not r.safe_to_mutate


def test_level1_tracking_token_is_exact():
    apps = [
        {"id": "app-token-abc-123", "company_domain": "uber.com", "company_name": "Uber",
         "job_title": "Backend", "apply_url": "", "status": "applied"}
    ]
    r = EmailApplicationMatcher().match(
        "noreply@uber.com", "uber.com",
        "Your Application Reference: app-token-abc-123",
        "We have received your application with ref app-token-abc-123.",
        apps
    )
    assert r.confidence == MatchConfidence.EXACT
    assert r.application_id == "app-token-abc-123"
    assert r.safe_to_mutate


def test_level2_url_match_is_exact():
    r = EmailApplicationMatcher().match(
        "jobs@postman.com", "postman.com",
        "Application received",
        "Thank you for applying at https://jobs.postman.com/123",
        make_apps("Postman")
    )
    assert r.confidence == MatchConfidence.EXACT
    assert r.application_id == "app-Postman"
    assert r.safe_to_mutate


def test_level3_company_and_role_unique_is_strong():
    apps = [
        {"id": "app-cred-backend", "company_domain": "cred.club", "company_name": "CRED",
         "job_title": "Backend Engineer", "apply_url": "https://careers.cred.club/1", "status": "saved"},
        {"id": "app-cred-frontend", "company_domain": "cred.club", "company_name": "CRED",
         "job_title": "Frontend Engineer", "apply_url": "https://careers.cred.club/2", "status": "saved"},
    ]
    r = EmailApplicationMatcher().match(
        "recruiting@cred.club", "cred.club",
        "CRED Backend Engineer Application Status",
        "Thank you for your interest in the Backend Engineer position at CRED.",
        apps
    )
    assert r.confidence == MatchConfidence.STRONG
    assert r.application_id == "app-cred-backend"
    assert r.safe_to_mutate


def test_level3_company_and_role_multiple_is_ambiguous():
    """
    If multiple applications exist for same company and same role title,
    Level 3 MUST return AMBIGUOUS (safe_to_mutate = False).
    """
    apps = [
        {"id": "app-google-swe-1", "company_domain": "google.com", "company_name": "Google",
         "job_title": "Software Engineer", "apply_url": "", "status": "applied"},
        {"id": "app-google-swe-2", "company_domain": "google.com", "company_name": "Google",
         "job_title": "Software Engineer", "apply_url": "", "status": "applied"},
    ]
    r = EmailApplicationMatcher().match(
        "recruiting@google.com", "google.com",
        "Google Software Engineer update",
        "Thank you for applying to Google as a Software Engineer.",
        apps
    )
    assert r.confidence == MatchConfidence.AMBIGUOUS
    assert r.application_id is None
    assert not r.safe_to_mutate
    assert set(r.application_ids_considered) == {"app-google-swe-1", "app-google-swe-2"}


def test_level4_and_level5_single_domain_match_is_probable():
    r = EmailApplicationMatcher().match(
        "hr@razorpay.com", "razorpay.com", "Your application update", "", make_apps("Razorpay")
    )
    assert r.confidence == MatchConfidence.PROBABLE
    assert r.application_id == "app-Razorpay"
    assert r.safe_to_mutate


def test_level5_multiple_apps_same_domain_is_ambiguous():
    """
    Critical invariant: Google SWE + ML + Intern -> AMBIGUOUS -> no mutation.
    """
    apps = [
        {"id": "app-swe",    "company_domain": "google.com", "company_name": "Google",
         "job_title": "SWE", "apply_url": "https://careers.google.com/swe", "status": "saved"},
        {"id": "app-ml",     "company_domain": "google.com", "company_name": "Google",
         "job_title": "ML Engineer", "apply_url": "https://careers.google.com/ml", "status": "saved"},
        {"id": "app-intern", "company_domain": "google.com", "company_name": "Google",
         "job_title": "AI Intern", "apply_url": "https://careers.google.com/intern", "status": "saved"},
    ]
    r = EmailApplicationMatcher().match(
        "noreply@google.com", "google.com",
        "We regret to inform you...", "Thank you for applying", apps
    )
    assert r.confidence == MatchConfidence.AMBIGUOUS
    assert r.application_id is None
    assert not r.safe_to_mutate
    assert len(r.application_ids_considered) == 3


def test_unknown_domain_no_match():
    r = EmailApplicationMatcher().match(
        "spam@unknown.com", "unknown.com", "Newsletter", "", make_apps("Razorpay")
    )
    assert r.confidence == MatchConfidence.NO_MATCH
    assert r.application_id is None
    assert not r.safe_to_mutate
