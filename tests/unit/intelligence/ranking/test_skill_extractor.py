"""
tests/unit/intelligence/ranking/test_skill_extractor.py

Unit tests for SkillExtractor keyword matching.
"""
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource
from intelligence.ranking.skill_extractor import SkillExtractor


def test_extract_from_job():
    extractor = SkillExtractor()
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="1",
        source_url="http://ex.com/1",
        title="Senior Python & FastAPI AI Engineer",
        company="Acme",
        description="We build LLM applications using PyTorch, Docker, PostgreSQL, and Redis.",
        skills=["Python", "FastAPI"],
    )

    skills = extractor.extract_from_job(job)
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PyTorch" in skills
    assert "Docker" in skills
    assert "PostgreSQL" in skills
    assert "Redis" in skills
    assert "LLM" in skills


def test_extract_from_profile():
    extractor = SkillExtractor()
    profile = CandidateProfile(
        name="Vinay",
        email="vinay@ex.com",
        location="India",
        graduation_year=2025,
        required_tech_stack=["Python", "FastAPI"],
        ideal_role_keywords=["AI Engineer"],
        experience_bullets=[
            "Engineered multi-agent AI systems with PyTorch and PostgreSQL.",
        ],
    )

    skills = extractor.extract_from_profile(profile)
    assert "Python" in skills
    assert "FastAPI" in skills
    assert "PyTorch" in skills
    assert "PostgreSQL" in skills
