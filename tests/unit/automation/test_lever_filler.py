"""
tests/unit/automation/test_lever_filler.py

Unit tests for LeverFormFiller play-by-play automation.
"""
import pytest
from unittest.mock import AsyncMock
from automation.fillers.lever import LeverFormFiller
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource


@pytest.mark.asyncio
async def test_lever_filler_standard_flow():
    filler = LeverFormFiller()

    mock_page = AsyncMock()
    mock_page.goto.return_value = True
    mock_page.query_selector.return_value = None
    mock_page.fill.return_value = True

    candidate = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
    )
    job = Job(
        source=JobSource.LEVER,
        source_id="lever_1",
        source_url="https://jobs.lever.co/acme/lever_1",
        apply_url="https://jobs.lever.co/acme/lever_1/apply",
        title="AI Engineer",
        company="Acme",
    )

    success = await filler.fill(mock_page, job, candidate, resume_path="/tmp/res.pdf")
    assert success is True
    mock_page.goto.assert_called_with("https://jobs.lever.co/acme/lever_1/apply")
