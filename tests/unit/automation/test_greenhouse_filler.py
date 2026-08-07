"""
tests/unit/automation/test_greenhouse_filler.py

Unit tests for GreenhouseFormFiller play-by-play automation & CAPTCHA detection.
"""
import pytest
from unittest.mock import AsyncMock
from automation.fillers.greenhouse import GreenhouseFormFiller, PauseRequired
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource


@pytest.mark.asyncio
async def test_greenhouse_filler_standard_flow():
    filler = GreenhouseFormFiller()

    mock_page = AsyncMock()
    mock_page.goto.return_value = True
    mock_page.query_selector.return_value = None  # No CAPTCHA
    mock_page.fill.return_value = True
    mock_page.set_input_files.return_value = True

    candidate = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
    )
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="101",
        source_url="https://boards.greenhouse.io/acme/jobs/101",
        apply_url="https://boards.greenhouse.io/acme/jobs/101#app",
        title="AI Engineer",
        company="Acme",
    )

    success = await filler.fill(mock_page, job, candidate, resume_path="/tmp/resume.pdf")
    assert success is True
    mock_page.goto.assert_called_with("https://boards.greenhouse.io/acme/jobs/101#app")


@pytest.mark.asyncio
async def test_greenhouse_filler_raises_pause_on_captcha():
    filler = GreenhouseFormFiller()

    mock_page = AsyncMock()
    mock_page.goto.return_value = True
    mock_page.query_selector.return_value = AsyncMock()  # CAPTCHA iframe present!

    candidate = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
    )
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="102",
        source_url="https://boards.greenhouse.io/acme/jobs/102",
        title="AI Engineer",
        company="Acme",
    )

    with pytest.raises(PauseRequired) as exc_info:
        await filler.fill(mock_page, job, candidate, resume_path="/tmp/resume.pdf")

    assert "CAPTCHA_DETECTED" in str(exc_info.value)
