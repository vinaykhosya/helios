"""
tests/unit/automation/test_replay.py

Unit tests for ReplayEngine snapshot loading and re-execution.
"""
import pytest
from automation.recovery import RecoverySnapshot
from automation.replay import ReplayEngine
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource


@pytest.mark.asyncio
async def test_replay_engine(tmp_path):
    html_file = tmp_path / "snap_1.html"
    meta_file = tmp_path / "snap_1.json"
    html_file.write_text("<html><body>Form</body></html>", encoding="utf-8")
    meta_file.write_text("{}", encoding="utf-8")

    snapshot = RecoverySnapshot(
        snapshot_id="snap_1",
        job_id="job_1",
        source="greenhouse",
        apply_url="https://boards.greenhouse.io/acme/1",
        error_message="Selector missing",
        html_snapshot_path=str(html_file),
        metadata_path=str(meta_file),
    )

    candidate = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
    )
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="1",
        source_url="https://boards.greenhouse.io/acme/1",
        apply_url="https://boards.greenhouse.io/acme/1",
        title="AI Dev",
        company="Acme",
    )

    engine = ReplayEngine()
    result = await engine.replay_from_snapshot(snapshot, job, candidate, resume_path="/tmp/res.pdf")
    assert result.snapshot_id == "snap_1"
    assert result.success is True
