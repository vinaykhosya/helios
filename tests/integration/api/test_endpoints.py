"""
tests/integration/api/test_endpoints.py

Integration tests for FastAPI endpoints: /health, /api/v1/jobs, and /api/v1/companies.
Uses httpx.AsyncClient to perform async API requests against the endpoints.
"""
import pytest
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine

from backend.src.main import app
from backend.src.core.di import DIContainer
from database.models import Base
from core.models.job import Job, JobSource
from core.models.company import Company


@pytest.fixture(scope="module")
def test_db_url():
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("No DATABASE_URL configured for integration tests. Skipping.")
    if "postgresql+asyncpg" not in url and "sqlite" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


@pytest.fixture(scope="module", autouse=True)
async def setup_test_database(test_db_url):
    """Initialize DB schema and load DIContainer for the test run."""
    # Build schema
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize DI Container with test url
    DIContainer.initialize(database_url=test_db_url)

    yield

    # Teardown
    await DIContainer.shutdown()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client():
    """Async HTTP client targeting the FastAPI application."""
    # Use ASGITransport to dispatch requests locally without a running HTTP server
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_companies_api_endpoints(client):
    company_data = {
        "name": "FastAPI Inc",
        "website": "https://fastapi.tiangolo.com",
        "industry": "Software",
    }

    # 1. POST Create Company
    post_res = await client.post("/api/v1/companies", json=company_data)
    assert post_res.status_code == 201
    created_company = post_res.json()
    assert created_company["name"] == "FastAPI Inc"
    assert created_company["id"] is not None

    # 2. GET List Companies
    list_res = await client.get("/api/v1/companies")
    assert list_res.status_code == 200
    companies_list = list_res.json()
    assert len(companies_list) >= 1
    assert any(c["name"] == "FastAPI Inc" for c in companies_list)

    # 3. GET Single Company by ID
    get_res = await client.get(f"/api/v1/companies/{created_company['id']}")
    assert get_res.status_code == 200
    fetched_company = get_res.json()
    assert fetched_company["id"] == created_company["id"]


@pytest.mark.asyncio
async def test_jobs_api_endpoints(client):
    # Register parent company first
    post_res = await client.post("/api/v1/companies", json={"name": "API Labs"})
    assert post_res.status_code == 201
    company = post_res.json()

    job_data = {
        "source": "lever",
        "source_id": "job-abc-123",
        "source_url": "https://lever.co/job/abc-123",
        "title": "Backend Architect",
        "company": company["name"],
        "company_id": company["id"],
    }

    # 1. POST Create Job
    post_job_res = await client.post("/api/v1/jobs", json=job_data)
    assert post_job_res.status_code == 201
    created_job = post_job_res.json()
    assert created_job["title"] == "Backend Architect"
    assert created_job["company_id"] == company["id"]

    # 2. GET List Jobs
    list_job_res = await client.get("/api/v1/jobs")
    assert list_job_res.status_code == 200
    jobs_list = list_job_res.json()
    assert len(jobs_list) >= 1
    assert any(j["source_id"] == "job-abc-123" for j in jobs_list)

    # 3. GET Single Job by ID
    get_job_res = await client.get(f"/api/v1/jobs/{created_job['id']}")
    assert get_job_res.status_code == 200
    fetched_job = get_job_res.json()
    assert fetched_job["id"] == created_job["id"]
