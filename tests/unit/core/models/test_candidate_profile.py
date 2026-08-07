"""
tests/unit/core/models/test_candidate_profile.py

Unit tests for CandidateProfile domain model.
"""
from core.models.candidate_profile import CandidateProfile


def test_candidate_profile_creation():
    profile = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
        years_of_experience=0.5,
        required_tech_stack=["Python", "FastAPI"],
        excluded_keywords=["PHP", "Sales"],
        target_locations=["India", "Remote"],
    )

    assert profile.name == "Vinay Khosya"
    assert profile.email == "vinay@example.com"
    assert profile.graduation_year == 2025
    assert profile.years_of_experience == 0.5
    assert "Python" in profile.required_tech_stack
    assert profile.willing_to_relocate is True
    assert profile.requires_sponsorship is False


def test_candidate_profile_defaults():
    profile = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
    )

    assert profile.max_experience_years == 3.0
    assert profile.job_types == ["full_time"]
    assert profile.required_tech_stack == []
    assert profile.excluded_keywords == []
