"""
tests/unit/ai/engines/test_profile_intelligence.py

Unit tests for ProfileIntelligenceAgent skill prioritization and bullet selection.
"""
from ai.engines.profile_intelligence import ProfileIntelligenceAgent
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource


def test_profile_intelligence_agent():
    profile = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
        required_tech_stack=["Python", "Docker", "FastAPI"],
        ideal_role_keywords=["AI Engineer"],
        experience_bullets=[
            "Built PyTorch LLM agent pipelines",
            "Deployed FastAPI Docker services to AWS",
            "Wrote standard SQL database queries",
        ],
    )

    agent = ProfileIntelligenceAgent(profile=profile)

    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="1",
        source_url="http://ex.com/1",
        title="AI LLM Engineer",
        company="Acme",
        description="Looking for PyTorch and LLM pipeline experience.",
        skills=["PyTorch", "LLM"],
    )

    skills = agent.get_skills_for_job(job)
    assert "Python" in skills

    bullets = agent.get_experience_bullets(job, max_bullets=2)
    assert len(bullets) == 2
    assert "PyTorch" in bullets[0]
