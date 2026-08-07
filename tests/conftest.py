"""
tests/conftest.py

Root pytest configuration and shared fixtures.
This file is automatically loaded by pytest before any tests run.

Conventions:
  - Fixtures that are needed across all test categories belong here.
  - Fixtures specific to a category (unit, integration, e2e) belong in
    that subdirectory's conftest.py.
  - All fixtures that touch external systems (DB, Redis, HTTP) must be
    async and use pytest-asyncio.
"""
import pytest


# ── Minimal Job fixture (no DB, no network) ───────────────────────────────────

@pytest.fixture
def minimal_job():
    """A Job with only required fields. Used by unit tests."""
    from core.models.job import Job, JobSource
    return Job(
        source=JobSource.JOBINDEX,
        source_id="test-001",
        source_url="https://jobindex.dk/job/test-001",
        title="Senior Data Scientist",
        company="Acme A/S",
    )


@pytest.fixture
def full_job(minimal_job):
    """A Job with all fields populated. Used by pipeline stage tests."""
    from core.models.job import RemotePolicy, EmploymentType, Salary, SalaryConfidence
    return minimal_job.model_copy(update={
        "location": "Copenhagen, Denmark",
        "city": "Copenhagen",
        "country": "Denmark",
        "remote": RemotePolicy.HYBRID,
        "employment_type": EmploymentType.FULL_TIME,
        "seniority": "senior",
        "experience_years": 5,
        "skills": ["Python", "Machine Learning", "SQL"],
        "industry": "Technology",
        "salary": Salary(min=700000, max=900000, currency="DKK", confidence=SalaryConfidence.EXPLICIT),
    })


@pytest.fixture
def sample_correlation_id():
    """A fixed correlation_id for tracing event chains in tests."""
    return "00000000-test-test-test-000000000001"
