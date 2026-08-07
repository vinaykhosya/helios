"""
tests/unit/intelligence/ranking/test_skill_match_scorer.py

Unit tests for SkillMatchScorer calculation.
"""
from intelligence.ranking.skill_match_scorer import SkillMatchScorer


def test_skill_match_scorer_partial_match():
    scorer = SkillMatchScorer()
    job_skills = ["Python", "FastAPI", "Docker", "Redis"]
    candidate_skills = ["Python", "FastAPI", "PostgreSQL"]

    result = scorer.score(job_skills, candidate_skills)
    assert result.overall_score == 0.5  # 2 of 4 matched
    assert sorted(result.matched_skills) == ["FastAPI", "Python"]
    assert sorted(result.missing_skills) == ["Docker", "Redis"]


def test_skill_match_scorer_full_match():
    scorer = SkillMatchScorer()
    job_skills = ["Python", "FastAPI"]
    candidate_skills = ["python", "fastapi", "docker"]

    result = scorer.score(job_skills, candidate_skills)
    assert result.overall_score == 1.0
    assert result.missing_skills == []


def test_skill_match_scorer_empty_job_skills():
    scorer = SkillMatchScorer()
    result = scorer.score([], ["Python"])
    assert result.overall_score == 1.0
    assert result.missing_skills == []
