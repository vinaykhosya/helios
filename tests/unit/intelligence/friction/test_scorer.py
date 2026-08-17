"""
tests/unit/intelligence/friction/test_scorer.py

Unit tests for FrictionScorer. All 6 tests from the plan + 2 edge-case extras.
"""
import pytest
from intelligence.friction.scorer import FrictionScorer, FrictionResult


def test_no_args_standard():
    r = FrictionScorer().score()
    assert r.label == "STANDARD" and r.score == 0


def test_one_question_moderate():
    r = FrictionScorer().score(custom_questions=["Why this role?"])
    assert r.score == 1
    assert r.label == "MODERATE"


def test_five_questions_heavy():
    r = FrictionScorer().score(custom_questions=["Q1", "Q2", "Q3", "Q4", "Q5"])
    assert r.score == 2
    assert r.label == "HEAVY"


def test_captcha_blocking():
    r = FrictionScorer().score(has_captcha=True)
    assert r.score == 3 and r.label == "BLOCKING"
    assert any("CAPTCHA" in reason for reason in r.reasons)


def test_video_blocking():
    r = FrictionScorer().score(has_video_questions=True)
    assert r.score == 3


def test_blocking_overrides_moderate():
    """CAPTCHA always wins even when there is also a moderate question."""
    r = FrictionScorer().score(custom_questions=["Q1"], has_captcha=True)
    assert r.score == 3


def test_multipage_heavy():
    """3 pages is HEAVY even with no questions."""
    r = FrictionScorer().score(page_count=3)
    assert r.score == 2
    assert r.label == "HEAVY"


def test_essay_questions_heavy():
    """Essay questions push score to HEAVY."""
    r = FrictionScorer().score(has_essay_questions=True)
    assert r.score == 2


def test_requires_account_creation_blocking():
    """Account creation is always BLOCKING."""
    r = FrictionScorer().score(requires_account_creation=True)
    assert r.score == 3


def test_result_is_pydantic_model():
    """FrictionResult must be a Pydantic model with the right fields."""
    r = FrictionScorer().score()
    assert isinstance(r, FrictionResult)
    assert isinstance(r.reasons, list)
    assert 0 <= r.score <= 3


def test_score_field_bounds():
    """score is always 0-3, never outside that range."""
    # Stack multiple heavy factors -- should cap at 3
    r = FrictionScorer().score(
        has_captcha=True, has_otp=True, has_video_questions=True,
        requires_account_creation=True, custom_questions=["Q"] * 10,
    )
    assert r.score == 3
