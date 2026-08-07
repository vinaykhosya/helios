"""
tests/integration/repositories/test_sqlalchemy_repos.py

Integration tests for SQLAlchemyJobRepository and SQLAlchemyCompanyRepository.
Requires a running PostgreSQL instance (or uses an environment-configured test DB).
"""
import pytest
import os
from datetime import datetime

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from core.models.job import Job, JobSource, RemotePolicy, EmploymentType
from core.models.company import Company, CompanySize
from database.models import Base
from backend.src.repositories.job import SQLAlchemyJobRepository
from backend.src.repositories.company import SQLAlchemyCompanyRepository


@pytest.fixture(scope="module")
def test_db_url():
    """Load database URL for testing from environment or use a fallback test DB."""
    # Use postgresql+asyncpg test db url
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("No DATABASE_URL configured for integration tests. Skipping.")
    if "postgresql+asyncpg" not in url and "sqlite" not in url:
        # force asyncpg driver if postgresql://
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


@pytest.fixture(scope="module")
async def test_engine(test_db_url):
    """Create async SQLAlchemy engine and migrate tables."""
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        # Create all tables on the test database
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        # Drop all tables after tests complete
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    """Yield a transactional AsyncSession rolling back changes after each test."""
    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_company_repository_crud(db_session):
    repo = SQLAlchemyCompanyRepository(db_session)
    company = Company(
        name="Google Denmark",
        website="https://google.dk",
        industry="Technology",
        size=CompanySize.ENTERPRISE,
    )

    # 1. Create
    created = await repo.create(company)
    assert created.id == company.id
    assert created.name == "Google Denmark"

    # 2. Get by ID
    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.name == "Google Denmark"
    assert fetched.website == "https://google.dk"

    # 3. Get by Normalized Name
    fetched_by_name = await repo.get_by_normalized_name("google denmark")
    assert fetched_by_name is not None
    assert fetched_by_name.id == created.id

    # 4. Update
    updated_company = fetched.model_copy(update={"website": "https://google.com"})
    updated = await repo.update(updated_company)
    assert updated.website == "https://google.com"

    # 5. List
    companies = await repo.list_companies(limit=5)
    assert len(companies) >= 1
    assert any(c.name == "Google Denmark" for c in companies)


@pytest.mark.asyncio
async def test_job_repository_crud(db_session):
    company_repo = SQLAlchemyCompanyRepository(db_session)
    job_repo = SQLAlchemyJobRepository(db_session)

    # Setup parent company profile
    company = Company(name="Test Co")
    company_created = await company_repo.create(company)

    job = Job(
        source=JobSource.JOBINDEX,
        source_id="test-job-999",
        source_url="https://jobindex.dk/job/test-job-999",
        title="Full Stack Engineer",
        company=company_created.name,
        company_id=company_created.id,
        remote=RemotePolicy.REMOTE,
        employment_type=EmploymentType.FULL_TIME,
        skills=["Python", "React", "PostgreSQL"],
    )

    # 1. Create
    created = await job_repo.create(job)
    assert created.id == job.id
    assert created.title == "Full Stack Engineer"
    assert created.company_id == company_created.id

    # 2. Get by ID
    fetched = await job_repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.source_id == "test-job-999"

    # 3. Get by Source ID
    fetched_by_src = await job_repo.get_by_source_id(JobSource.JOBINDEX.value, "test-job-999")
    assert fetched_by_src is not None
    assert fetched_by_src.id == created.id

    # 4. Update
    updated_job = fetched.model_copy(update={"title": "Senior Full Stack Engineer"})
    updated = await job_repo.update(updated_job)
    assert updated.title == "Senior Full Stack Engineer"

    # 5. List
    jobs = await job_repo.list_jobs(limit=5)
    assert len(jobs) >= 1
    assert any(j.source_id == "test-job-999" for j in jobs)

    # 6. Delete
    deleted = await job_repo.delete(created.id)
    assert deleted is True

    fetched_after_delete = await job_repo.get_by_id(created.id)
    assert fetched_after_delete is None
