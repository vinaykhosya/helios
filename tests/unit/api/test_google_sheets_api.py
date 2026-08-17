"""
tests/unit/api/test_google_sheets_api.py

API integration tests for Google Sheets endpoints.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.src.main import app
from backend.src.core.di import DIContainer
from database.models.base import Base
from database.models.integrations import GoogleSheetsConfigORM


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
async def test_get_sheets_status(test_app_and_session):
    client, _ = test_app_and_session
    resp = await client.get("/api/google-sheets/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "connected" in data
    assert data["worksheet"] == "Helios Queue"
    assert data["mode"] == "push_only_v1"


@pytest.mark.asyncio
async def test_connect_sheets_without_service_account_returns_error(test_app_and_session):
    client, _ = test_app_and_session
    with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": ""}, clear=False):
        resp = await client.post("/api/google-sheets/connect?spreadsheet_id=sample-id")
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data
        assert "GOOGLE_SERVICE_ACCOUNT_JSON" in data["error"]


@pytest.mark.asyncio
async def test_connect_sheets_persists_config(test_app_and_session):
    client, session_maker = test_app_and_session
    with patch.dict("os.environ", {"GOOGLE_SERVICE_ACCOUNT_JSON": '{"type": "service_account"}'}, clear=False):
        with patch("integrations.google_sheets.client.GoogleSheetsClient.get_worksheet") as mock_get:
            mock_get.return_value = MagicMock()
            resp = await client.post(
                "/api/google-sheets/connect?spreadsheet_id=persisted-sheet-123",
                headers={"X-User-ID": "user_sheet_test"},
            )
            assert resp.status_code == 200
            assert resp.json() == {"status": "connected", "spreadsheet_id": "persisted-sheet-123"}

            # Verify persisted in database
            async with session_maker() as session:
                from sqlalchemy import select
                res = await session.execute(
                    select(GoogleSheetsConfigORM).where(GoogleSheetsConfigORM.user_id == "user_sheet_test")
                )
                cfg = res.scalar_one_or_none()
                assert cfg is not None
                assert cfg.spreadsheet_id == "persisted-sheet-123"
                assert cfg.is_active is True

            # Verify GET /status reflects the active DB config
            status_resp = await client.get("/api/google-sheets/status", headers={"X-User-ID": "user_sheet_test"})
            assert status_resp.status_code == 200
            assert status_resp.json()["connected"] is True
            assert status_resp.json()["spreadsheet_id"] == "persisted-sheet-123"
