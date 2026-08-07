"""
tests/integration/pipeline/test_persistence_stage.py

Integration tests for the Ingestion Pipeline's PersistenceStage.
Verifies that jobs pass through correctly, link/create companies, and upsert database records.
"""
import pytest
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.models.job import Job, JobSource
from database.models import Base
from backend.src.repositories.job import SQLAlchemyJobRepository
from backend.src.repositories.company import SQLAlchemyCompanyRepository
from intelligence.pipeline.stages import CompanyResolverStage, PersistenceStage


@pytest.fixture(scope="module")
def test_db_url():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("No DATABASE_URL configured for integration tests. Skipping.")
    if "postgresql+asyncpg" not in url and "sqlite" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


@pytest.fixture(scope="module")
async def test_engine(test_db_url):
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_persistence_stage_process(db_session):
    job_repo = SQLAlchemyJobRepository(db_session)
    company_repo = SQLAlchemyCompanyRepository(db_session)

    resolver_stage = CompanyResolverStage(company_repo=company_repo)
    persist_stage = PersistenceStage(job_repo=job_repo)

    job1 = Job(
        source=JobSource.GREENHOUSE,
        source_id="gh-101",
        source_url="https://greenhouse.io/company/job/101",
        title="Software Engineer",
        company="Greenhouse Co",
    )

    # 1. Resolve company
    resolved = await resolver_stage.process([job1])
    assert len(resolved) == 1
    assert resolved[0].company_id is not None

    # 2. Persist job
    result = await persist_stage.process(resolved)
    assert len(result) == 1
    persisted_job = result[0]
    assert persisted_job.source_id == "gh-101"
    assert persisted_job.company_id == resolved[0].company_id

    # Check database directly via repositories
    db_company = await company_repo.get_by_id(persisted_job.company_id)
    assert db_company is not None
    assert db_company.name == "Greenhouse Co"

    db_job = await job_repo.get_by_id(persisted_job.id)
    assert db_job is not None
    assert db_job.title == "Software Engineer"

    # 3. Process again with modified title (this should trigger an update, not a new job)
    job1_modified = job1.model_copy(update={"title": "Senior Software Engineer"})
    resolved_update = await resolver_stage.process([job1_modified])
    result_update = await persist_stage.process(resolved_update)
    assert len(result_update) == 1
    updated_job = result_update[0]
    assert updated_job.id == persisted_job.id   # ID must be preserved!
    assert updated_job.title == "Senior Software Engineer"

    # Verify update in DB
    db_job_updated = await job_repo.get_by_id(persisted_job.id)
    assert db_job_updated.title == "Senior Software Engineer"
