"""
tests/integration/pipeline/test_end_to_end_ingestion.py

End-to-end integration test validating the entire ingestion architecture:
Greenhouse API mock -> Connector -> Event Bus -> Ingestion Worker -> Ingestion Pipeline -> DB.
"""
import pytest
import os
import httpx
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.models.job import JobSource
from core.events.bus import InMemoryEventBus
from database.models import Base
from backend.src.repositories.job import SQLAlchemyJobRepository
from backend.src.repositories.company import SQLAlchemyCompanyRepository
from backend.src.connectors.greenhouse import GreenhouseConnector
from backend.src.connectors.runner import ConnectorRunner
from workers.ingestion_worker import IngestionWorker


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
async def test_end_to_end_greenhouse_ingestion(db_session):
    # 1. Initialize Event Bus
    bus = InMemoryEventBus()

    # 2. Instantiate repositories
    job_repo = SQLAlchemyJobRepository(db_session)
    company_repo = SQLAlchemyCompanyRepository(db_session)

    # 3. Instantiate IngestionWorker (registers event subscribers)
    worker = IngestionWorker(event_bus=bus, job_repo=job_repo, company_repo=company_repo)

    # 4. Instantiate GreenhouseConnector with mocked HTTP client responses
    connector = GreenhouseConnector(board_token="netflix")
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jobs": [
            {
                "id": 98765,
                "title": "Lead Software Architect",
                "location": {"name": "Los Gatos, CA"},
                "content": "<p>We are looking for a Lead Architect. Must know <b>Python</b>.</p>",
            }
        ]
    }
    connector.client.get = AsyncMock(return_value=mock_response)

    # 5. Instantiate ConnectorRunner
    runner = ConnectorRunner(event_bus=bus, timeout_seconds=2.0)

    # 6. Run search (triggers events -> worker -> pipeline -> DB)
    events_published = await runner.run_search(connector, query="Architect")

    # Assertions
    assert len(events_published) == 1
    assert events_published[0].source_id == "98765"

    # Query DB to verify job exists
    persisted_job = await job_repo.get_by_source_id(JobSource.GREENHOUSE.value, "98765")
    assert persisted_job is not None
    assert persisted_job.title == "Lead Software Architect"
    # Description should be normalized (HTML tags stripped!)
    assert persisted_job.description == "We are looking for a Lead Architect. Must know Python."

    # Query DB to verify company exists
    assert persisted_job.company_id is not None
    persisted_company = await company_repo.get_by_id(persisted_job.company_id)
    assert persisted_company is not None
    assert persisted_company.name == "Netflix"
