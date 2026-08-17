"""
tests/unit/intelligence/ranking/test_seniority_separation.py

Unit tests for Seniority-Eligibility separation and 5-dimension weighted scoring.
"""
import pytest
from core.models.job import Job, JobSource, RemotePolicy
from core.models.candidate_profile import CandidateProfile
from intelligence.ranking.ranker import RankingAgent


def test_seniority_mismatch_flagged_for_senior_roles():
    profile = CandidateProfile(
        id="ai_ml",
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2027,
        years_of_experience=1.0,
        max_experience_years=3.0,
        required_tech_stack=["Python", "FastAPI"],
        target_locations=["India", "Remote"],
        ideal_role_keywords=["AI Engineer", "Software Engineer"],
    )

    ranker = RankingAgent(profile)

    # 1. Junior / Fresher Friendly Job (Eligible)
    junior_job = Job(
        source=JobSource.LINKEDIN,
        source_id="j1",
        source_url="https://linkedin.com/jobs/1",
        title="Software Engineer - AI Systems",
        company="Razorpay",
        location="Bangalore, India",
        experience_years=1,
        skills=["Python", "FastAPI", "PyTorch"],
    )

    result_junior = ranker.rank(junior_job)
    assert junior_job.eligibility_status == "ELIGIBLE"
    assert junior_job.dimension_breakdown["tech_stack"] > 0.5
    assert junior_job.dimension_breakdown["seniority"] == 1.0

    # 2. Senior / Managerial Job (Seniority Mismatch)
    senior_job = Job(
        source=JobSource.LINKEDIN,
        source_id="j2",
        source_url="https://linkedin.com/jobs/2",
        title="Principal Architect / Engineering Manager",
        company="Microsoft",
        location="Bangalore, India",
        experience_years=7,
        skills=["Python", "FastAPI", "System Design"],
    )

    result_senior = ranker.rank(senior_job)
    assert senior_job.eligibility_status == "SENIORITY_MISMATCH"
    assert senior_job.dimension_breakdown["seniority"] < 0.7
    assert len(senior_job.eligibility_reasons) > 0
    assert result_senior.recommendation == "seniority_review"
