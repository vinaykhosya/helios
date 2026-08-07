"""
tests/unit/automation/test_notification.py

Unit tests for TelegramNotifier formatting and approval lifecycle.
"""
import pytest
from automation.notification import TelegramNotifier
from core.models.job import Job, JobSource
from intelligence.ranking.ranker import RankingResult, MatchDimension


@pytest.mark.asyncio
async def test_telegram_notifier_formatting_and_lifecycle():
    notifier = TelegramNotifier()
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="1",
        source_url="http://ex.com/1",
        title="AI Engineer",
        company="Siemens",
        location="India",
    )
    ranking = RankingResult(
        job_id=str(job.id),
        overall_score=0.90,
        confidence=0.95,
        dimensions=[MatchDimension(name="Tech", score=1.0, weight=1.0, matched=True)],
        missing_skills=["Docker"],
        recommendation="ask_user",
        reason="Good match",
    )

    pending = await notifier.send_approval_request(job, ranking, pause_reason="CAPTCHA_DETECTED")
    assert pending.status == "pending"
    assert pending.job_title == "AI Engineer"

    # User responds /approve
    success = await notifier.respond(pending.id, approved=True)
    assert success is True
    assert pending.status == "approved"
