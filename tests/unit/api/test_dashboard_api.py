"""
tests/unit/api/test_dashboard_api.py

API integration tests for Dashboard ROI metrics endpoint.
"""
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.src.main import app
from backend.src.core.di import DIContainer
from database.models.base import Base
from backend.src.repositories.application import SQLAlchemyApplicationRepository
from core.models.application import Application, ApplicationStatus


@pytest.fixture
async def test_app_and_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        execution_options={"schema_translate_map": {"helios": None}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def override_session():
        async with session_maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            finally:
                await s.close()

    original_session = DIContainer.session
    DIContainer.session = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client, session_maker

    DIContainer.session = original_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_dashboard_metrics(test_app_and_session):
    client, session_maker = test_app_and_session
    user_id = "user_dash_test"

    async with session_maker() as session:
        repo = SQLAlchemyApplicationRepository(session)
        await repo.create(Application(id=str(uuid.uuid4()), user_id=user_id, job_id="j1", status=ApplicationStatus.SUBMITTED_MANUAL))
        await repo.create(Application(id=str(uuid.uuid4()), user_id=user_id, job_id="j2", status=ApplicationStatus.PHONE_SCREEN))
        await repo.create(Application(id=str(uuid.uuid4()), user_id=user_id, job_id="j3", status=ApplicationStatus.OFFER))
        await repo.create(Application(id=str(uuid.uuid4()), user_id=user_id, job_id="j4", status=ApplicationStatus.REJECTED))
        await session.commit()

    resp = await client.get("/api/dashboard/metrics", headers={"X-User-ID": user_id})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_applications"] == 4
    assert data["submitted_total"] == 4
    assert data["no_response"] == 1
    assert data["responses"] == 3
    assert data["rejections"] == 1
    assert data["positive_responses"] == 2
    assert data["phone_screens"] == 1
    assert data["offers"] == 1
    assert data["response_rate"] == 0.75          # 3 responses / 4 submitted
    assert data["positive_response_rate"] == 0.50 # 2 positive / 4 submitted
    assert data["offer_rate"] == 0.25             # 1 offer / 4 submitted
