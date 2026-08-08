"""
tests/test_verifier_and_router.py

Unit tests for JobFreshnessVerifier, Evidence Scoring, and PortalRouter.
"""
import pytest
from unittest.mock import AsyncMock
from automation.verifier import verify_job_freshness, verify_post_submission_evidence
from automation.portals.router import PortalRouter


@pytest.mark.asyncio
async def test_freshness_verifier_404():
    mock_page = AsyncMock()
    mock_page.title = AsyncMock(return_value="404 Not Found")
    
    res = await verify_job_freshness(mock_page, "https://jobs.lever.co/test/404-slug")
    assert not res.is_fresh
    assert res.status_code == "FAILED_404"


@pytest.mark.asyncio
async def test_freshness_verifier_closed_keywords():
    mock_page = AsyncMock()
    mock_page.title = AsyncMock(return_value="Software Engineer")
    mock_page.inner_text = AsyncMock(return_value="Thank you for your interest. This position has been filled.")
    
    res = await verify_job_freshness(mock_page, "https://jobs.lever.co/test/closed-slug")
    assert not res.is_fresh
    assert res.status_code == "CLOSED"


@pytest.mark.asyncio
async def test_evidence_scoring_unclicked_submit_rejected():
    mock_page = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="Thank you for applying to Siemens! We have received your application.")
    mock_page.url = "https://jobs.siemens.com/submitted"

    # GOLDEN RULE: If submit_clicked is False, synthetic IDs or DOM text MUST NOT result in CONFIRMED_APPLIED
    res = await verify_post_submission_evidence(
        mock_page,
        submit_clicked=False,
        live_application_id="REQ-99481",
        application_id_source="LIVE_PORTAL_DOM"
    )
    assert res.status == "SUBMISSION_UNVERIFIED"
    assert res.score == "WEAK"
    assert res.evidence_details["submit_clicked"] is False


@pytest.mark.asyncio
async def test_evidence_scoring_strong_submitted():
    mock_page = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="Thanks for applying! We have received your application.")
    mock_page.url = "https://jobs.lever.co/cred/thanks"

    res = await verify_post_submission_evidence(
        mock_page,
        submit_clicked=True,
        live_application_id="REQ-LIVE-99481",
        application_id_source="LIVE_PORTAL_DOM"
    )
    assert res.status == "CONFIRMED_APPLIED"
    assert res.score == "STRONG"
    assert res.evidence_details["submit_clicked"] is True
    assert res.evidence_details["dom_confirmation"] is True
    assert res.evidence_details["application_id"] == "REQ-LIVE-99481"


@pytest.mark.asyncio
async def test_evidence_scoring_weak_form_filled():
    mock_page = AsyncMock()
    mock_page.inner_text = AsyncMock(return_value="Contact us if you have any questions.")
    mock_page.url = "https://jobs.lever.co/test/job-id"

    res = await verify_post_submission_evidence(mock_page, submit_clicked=True)
    # Form filled without DOM confirmation text MUST NOT be marked CONFIRMED_APPLIED
    assert res.status == "SUBMISSION_UNVERIFIED"
    assert res.score == "WEAK"


def test_portal_router():
    ats, comp = PortalRouter.route_url("https://jobs.lever.co/cred/7e4d512e")
    assert ats == "lever"
    assert comp == "cred"

    ats_gh, comp_gh = PortalRouter.route_url("https://boards.greenhouse.io/postman/jobs/5912345")
    assert ats_gh == "greenhouse"
    assert comp_gh == "postman"

    ats_wd, comp_wd = PortalRouter.route_url("https://siemens.wd3.myworkdayjobs.com/Siemens_Careers")
    assert ats_wd == "workday"
    assert comp_wd == "siemens"
