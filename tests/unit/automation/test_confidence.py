"""
tests/unit/automation/test_confidence.py

Unit tests for ConfidenceEngine application decision threshold logic.
"""
from automation.confidence import ConfidenceEngine, ApplicationDecision
from intelligence.ranking.ranker import RankingResult, MatchDimension


def test_confidence_engine_auto_apply():
    engine = ConfidenceEngine()
    ranking = RankingResult(
        job_id="job_1",
        overall_score=0.92,
        confidence=0.98,
        dimensions=[MatchDimension(name="Tech", score=1.0, weight=1.0, matched=True)],
        missing_skills=[],
        recommendation="auto_apply",
        reason="High match",
    )

    decision = engine.decide(ranking, form_complexity=0)
    assert decision == ApplicationDecision.AUTO_APPLY


def test_confidence_engine_ask_user_due_to_complexity():
    engine = ConfidenceEngine()
    ranking = RankingResult(
        job_id="job_2",
        overall_score=0.90,
        confidence=0.96,
        dimensions=[MatchDimension(name="Tech", score=0.9, weight=1.0, matched=True)],
        missing_skills=[],
        recommendation="auto_apply",
        reason="High match",
    )

    # Complexity penalty of 2 (0.10 penalty drops 0.96 to 0.86)
    decision = engine.decide(ranking, form_complexity=2)
    assert decision == ApplicationDecision.ASK_USER


def test_confidence_engine_review():
    engine = ConfidenceEngine()
    ranking = RankingResult(
        job_id="job_3",
        overall_score=0.65,
        confidence=0.70,
        dimensions=[],
        missing_skills=["Docker"],
        recommendation="review",
        reason="Low match",
    )

    decision = engine.decide(ranking, form_complexity=0)
    assert decision == ApplicationDecision.REVIEW
