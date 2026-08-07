"""
tests/unit/workers/test_briefing.py

Unit tests for MorningBriefingGenerator text formatting.
"""
from shared.telemetry.metrics import HeliosSessionMetrics
from workers.briefing import MorningBriefingGenerator


def test_morning_briefing_generator_format():
    generator = MorningBriefingGenerator()
    metrics = HeliosSessionMetrics(
        session_id="sess_1",
        jobs_scanned=1200,
        jobs_eligible=45,
        excellent_matches=12,
        auto_applied=8,
        awaiting_approval=2,
        paused_captcha=1,
        rejection_reasons={"Title contains excluded keyword": 20, "Experience too high": 15},
        avg_application_time_seconds=28.5,
    )

    briefing = generator.format_briefing(metrics)
    assert "Good morning Vinay" in briefing
    assert "1,200" in briefing
    assert "28.5 seconds" in briefing
    assert "Title contains excluded keyword" in briefing
