"""
tests/unit/intelligence/ranking/test_eligibility.py

Unit tests for EligibilityGate hard constraint filtering.
"""
import pytest
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, EmploymentType, JobSource, RemotePolicy
from intelligence.ranking.eligibility import EligibilityGate


@pytest.fixture
def sample_profile():
    return CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
        years_of_experience=0.5,
        max_experience_years=3.0,
        required_tech_stack=["Python"],
        excluded_keywords=["PHP", "Sales", "Staffing"],
        target_locations=["India", "Remote"],
        excluded_companies=["BadCorp"],
        job_types=["full_time"],
    )


def test_eligibility_passes_valid_job(sample_profile):
    gate = EligibilityGate(sample_profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="101",
        source_url="https://boards.greenhouse.io/acme/jobs/101",
        title="AI Engineer",
        company="Acme Corp",
        description="We are looking for a Python developer with 1+ years experience in ML.",
        location="India",
        skills=["Python", "FastAPI"],
        employment_type=EmploymentType.FULL_TIME,
    )
    result = gate.check(job)
    assert result.eligible is True
    assert result.rejection_reasons == []


def test_eligibility_rejects_excluded_title_keyword(sample_profile):
    gate = EligibilityGate(sample_profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="102",
        source_url="https://boards.greenhouse.io/acme/jobs/102",
        title="PHP & Python Developer",
        company="Acme Corp",
        description="Python backend developer role",
        location="India",
        skills=["Python"],
    )
    result = gate.check(job)
    assert result.eligible is False
    assert any("Title contains excluded keyword: 'PHP'" in r for r in result.rejection_reasons)


def test_eligibility_rejects_excluded_description_keyword(sample_profile):
    gate = EligibilityGate(sample_profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="103",
        source_url="https://boards.greenhouse.io/acme/jobs/103",
        title="Software Engineer",
        company="Acme Corp",
        description="This position is managed by a Staffing agency for Python dev",
        location="India",
        skills=["Python"],
    )
    result = gate.check(job)
    assert result.eligible is False
    assert any("Description contains excluded keyword: 'Staffing'" in r for r in result.rejection_reasons)


def test_eligibility_rejects_excluded_company(sample_profile):
    gate = EligibilityGate(sample_profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="104",
        source_url="https://boards.greenhouse.io/badcorp/jobs/104",
        title="Python Engineer",
        company="BadCorp Inc",
        description="Python developer role",
        location="India",
        skills=["Python"],
    )
    result = gate.check(job)
    assert result.eligible is False
    assert any("Company 'BadCorp Inc' is on exclusion list" in r for r in result.rejection_reasons)


def test_eligibility_rejects_missing_required_tech(sample_profile):
    gate = EligibilityGate(sample_profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="105",
        source_url="https://boards.greenhouse.io/acme/jobs/105",
        title="Java Developer",
        company="Acme Corp",
        description="Java Spring Boot developer role",
        location="India",
        skills=["Java", "Spring"],
    )
    result = gate.check(job)
    assert result.eligible is False
    assert any("No required tech stack found" in r for r in result.rejection_reasons)


def test_eligibility_rejects_unmatched_location(sample_profile):
    gate = EligibilityGate(sample_profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="106",
        source_url="https://boards.greenhouse.io/acme/jobs/106",
        title="Python Engineer",
        company="Acme Corp",
        description="Python developer role in London UK",
        location="London, UK",
        remote=RemotePolicy.ON_SITE,
        skills=["Python"],
    )
    result = gate.check(job)
    assert result.eligible is False
    assert any("Location 'London, UK' not in target locations" in r for r in result.rejection_reasons)


def test_eligibility_rejects_experience_too_high(sample_profile):
    gate = EligibilityGate(sample_profile)
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="107",
        source_url="https://boards.greenhouse.io/acme/jobs/107",
        title="Senior Python Architect",
        company="Acme Corp",
        description="Requires 7+ years of experience with Python and distributed systems",
        location="India",
        skills=["Python"],
    )
    result = gate.check(job)
    assert result.eligible is False
    assert any("Requires 7+ years experience" in r for r in result.rejection_reasons)


@pytest.mark.asyncio
async def test_filter_batch_and_summarize(sample_profile):
    gate = EligibilityGate(sample_profile)
    jobs = [
        Job(source=JobSource.GREENHOUSE, source_id="201", source_url="http://ex.com/201", title="Python Dev", company="GoodCo", description="Python 1 yr exp", location="India"),
        Job(source=JobSource.GREENHOUSE, source_id="202", source_url="http://ex.com/202", title="PHP Dev", company="GoodCo", description="PHP 1 yr exp", location="India"),
        Job(source=JobSource.GREENHOUSE, source_id="203", source_url="http://ex.com/203", title="Java Senior", company="GoodCo", description="Java 7+ years of experience", location="UK"),
    ]
    eligible_jobs, results = await gate.filter_batch(jobs)
    assert len(eligible_jobs) == 1
    assert eligible_jobs[0].title == "Python Dev"

    stats = gate.summarize_session(results)
    assert stats.total_scanned == 3
    assert stats.total_eligible == 1
    assert stats.rejection_counts["Title contains excluded keyword"] == 1
