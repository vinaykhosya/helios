"""
tests/unit/intelligence/ranking/test_ranker.py

Unit tests for RankingAgent multi-dimensional scoring.
"""
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource, RemotePolicy
from intelligence.ranking.ranker import RankingAgent


def test_ranking_agent_high_match_auto_apply():
    profile = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
        required_tech_stack=["Python", "FastAPI"],
        target_locations=["India", "Remote"],
        ideal_role_keywords=["AI Engineer", "Software Engineer"],
    )
    agent = RankingAgent(profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="1",
        source_url="http://ex.com/1",
        title="AI Engineer",
        company="Acme Corp",
        description="Looking for Python and FastAPI skills",
        location="India",
        remote=RemotePolicy.REMOTE,
        skills=["Python", "FastAPI"],
    )

    result = agent.rank(job)
    assert result.overall_score >= 0.85
    assert result.recommendation == "auto_apply"
    assert result.confidence >= 0.95


def test_ranking_agent_partial_match_ask_user():
    profile = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
        required_tech_stack=["Python"],
        target_locations=["India"],
        ideal_role_keywords=["AI Engineer"],
    )
    agent = RankingAgent(profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="2",
        source_url="http://ex.com/2",
        title="DevOps Engineer",
        company="Acme Corp",
        description="Python script engineer with Kubernetes",
        location="India",
        skills=["Python", "Kubernetes"],
    )

    result = agent.rank(job)
    assert 0.70 <= result.confidence < 0.95
    assert result.recommendation in ["ask_user", "review"]
    assert "Kubernetes" in result.missing_skills
