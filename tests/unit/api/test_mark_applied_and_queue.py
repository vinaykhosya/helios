"""
tests/unit/api/test_mark_applied_and_queue.py

Comprehensive tests for Human Queue and Mark Applied flows with atomicity and security hardening.
"""
import os
import uuid
import pytest
from datetime import datetime
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from cryptography.fernet import Fernet

# Set fixed test secret before importing services
TEST_SECRET = Fernet.generate_key().decode()
os.environ["HELIOS_ACTION_TOKEN_SECRET"] = TEST_SECRET
os.environ["TELEGRAM_WEBHOOK_SECRET"] = "test_webhook_secret_123"

from backend.src.main import app
from backend.src.core.di import DIContainer
from backend.src.services.action_token_service import ActionTokenService
from core.models.application import Application, ApplicationStatus
from core.models.human_queue import HumanQueueEntry
from database.models.base import Base
from backend.src.repositories.application import SQLAlchemyApplicationRepository
from backend.src.repositories.human_queue import SQLAlchemyHumanQueueRepository


@pytest.fixture
async def test_app_and_session():
    """Sets up an in-memory SQLite database and yields an AsyncClient bound to the app."""
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
async def test_get_mark_applied_page_valid(test_app_and_session):
    client, session_maker = test_app_and_session
    user_id = "user_default"
    app_id = f"app-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        await app_repo.create(Application(
            id=app_id,
            user_id=user_id,
            job_id="job-1",
            status=ApplicationStatus.PENDING_MANUAL,
        ))
        await session.commit()

    token = ActionTokenService().create_mark_applied_token(app_id, user_id)

    # 1. GET page returns 200 HTML with form
    resp = await client.get(f"/mark-applied/{token}")
    assert resp.status_code == 200
    assert "Confirm Application" in resp.text
    assert f"/api/applications/{app_id}/mark-applied" in resp.text
    assert token in resp.text

    # 2. INVARIANT #7: GET must NEVER mutate state
    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        app_db = await app_repo.get_by_id(app_id)
        assert app_db.status == ApplicationStatus.PENDING_MANUAL
        assert app_db.applied_at is None


@pytest.mark.asyncio
async def test_get_mark_applied_page_invalid_token(test_app_and_session):
    client, _ = test_app_and_session
    resp = await client.get("/mark-applied/invalid_tampered_token_xyz")
    assert resp.status_code == 400
    assert "Link Invalid or Expired" in resp.text


@pytest.mark.asyncio
async def test_get_mark_applied_page_expired_token(test_app_and_session):
    client, _ = test_app_and_session
    token = ActionTokenService().create_mark_applied_token("app-1", "user-1", ttl_hours=-1)
    resp = await client.get(f"/mark-applied/{token}")
    assert resp.status_code == 400
    assert "Link Invalid or Expired" in resp.text


@pytest.mark.asyncio
async def test_get_mark_applied_page_nonexistent_application(test_app_and_session):
    client, _ = test_app_and_session
    token = ActionTokenService().create_mark_applied_token("nonexistent-app", "user-1")
    resp = await client.get(f"/mark-applied/{token}")
    assert resp.status_code == 404
    assert "Application not found" in resp.text


@pytest.mark.asyncio
async def test_get_mark_applied_page_already_applied(test_app_and_session):
    client, session_maker = test_app_and_session
    user_id = "user_default"
    app_id = f"app-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        await app_repo.create(Application(
            id=app_id,
            user_id=user_id,
            job_id="job-1",
            status=ApplicationStatus.SUBMITTED_MANUAL,
            applied_at=datetime.utcnow(),
        ))
        await session.commit()

    token = ActionTokenService().create_mark_applied_token(app_id, user_id)
    resp = await client.get(f"/mark-applied/{token}")
    assert resp.status_code == 200
    assert "Already Recorded" in resp.text


@pytest.mark.asyncio
async def test_post_mark_applied_successful_flow(test_app_and_session):
    client, session_maker = test_app_and_session
    user_id = "user_default"
    app_id = f"app-{uuid.uuid4()}"
    queue_id = f"queue-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        queue_repo = SQLAlchemyHumanQueueRepository(session)
        await app_repo.create(Application(
            id=app_id,
            user_id=user_id,
            job_id="job-1",
            status=ApplicationStatus.PENDING_MANUAL,
        ))
        await queue_repo.enqueue(HumanQueueEntry(
            id=queue_id,
            user_id=user_id,
            job_id="job-1",
            application_id=app_id,
            decision="pending",
        ))
        await session.commit()

    token = ActionTokenService().create_mark_applied_token(app_id, user_id)

    # Perform POST submission
    resp = await client.post(f"/api/applications/{app_id}/mark-applied", data={"token": token})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "recorded"
    assert data["application_id"] == app_id

    # Verify DB state: Application is SUBMITTED_MANUAL and Queue is completed
    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        queue_repo = SQLAlchemyHumanQueueRepository(session)

        app_db = await app_repo.get_by_id(app_id)
        assert app_db.status == ApplicationStatus.SUBMITTED_MANUAL
        assert app_db.applied_at is not None

        queue_db = await queue_repo.get_by_id(queue_id)
        assert queue_db.decision == "completed"
        assert queue_db.decided_at is not None


@pytest.mark.asyncio
async def test_post_mark_applied_fails_if_queue_in_terminal_state(test_app_and_session):
    """
    If HumanQueue is in terminal state 'skipped', mark applied MUST fail and rollback application.
    """
    client, session_maker = test_app_and_session
    user_id = "user_default"
    app_id = f"app-{uuid.uuid4()}"
    queue_id = f"queue-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        queue_repo = SQLAlchemyHumanQueueRepository(session)
        await app_repo.create(Application(
            id=app_id,
            user_id=user_id,
            job_id="job-1",
            status=ApplicationStatus.PENDING_MANUAL,
        ))
        await queue_repo.enqueue(HumanQueueEntry(
            id=queue_id,
            user_id=user_id,
            job_id="job-1",
            application_id=app_id,
            decision="pending",
        ))
        await queue_repo.decide(queue_id, "skipped")
        await session.commit()

    token = ActionTokenService().create_mark_applied_token(app_id, user_id)

    resp = await client.post(f"/api/applications/{app_id}/mark-applied", data={"token": token})
    assert resp.status_code == 400
    assert "terminal state 'skipped'" in resp.json()["detail"]

    # Verify application was NOT mutated (atomic rollback)
    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        app_db = await app_repo.get_by_id(app_id)
        assert app_db.status == ApplicationStatus.PENDING_MANUAL
        assert app_db.applied_at is None


@pytest.mark.asyncio
async def test_post_mark_applied_idempotent_duplicate(test_app_and_session):
    client, session_maker = test_app_and_session
    user_id = "user_default"
    app_id = f"app-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        await app_repo.create(Application(
            id=app_id,
            user_id=user_id,
            job_id="job-1",
            status=ApplicationStatus.SUBMITTED_MANUAL,
            applied_at=datetime.utcnow(),
        ))
        await session.commit()

    token = ActionTokenService().create_mark_applied_token(app_id, user_id)

    resp = await client.post(f"/api/applications/{app_id}/mark-applied", data={"token": token})
    assert resp.status_code == 200
    assert resp.json()["status"] == "already_recorded"


@pytest.mark.asyncio
async def test_post_mark_applied_wrong_user_token(test_app_and_session):
    client, session_maker = test_app_and_session
    app_id = f"app-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        await app_repo.create(Application(
            id=app_id,
            user_id="user_owner",
            job_id="job-1",
            status=ApplicationStatus.PENDING_MANUAL,
        ))
        await session.commit()

    token = ActionTokenService().create_mark_applied_token(app_id, "user_attacker")

    resp = await client.post(f"/api/applications/{app_id}/mark-applied", data={"token": token})
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Unauthorized"


@pytest.mark.asyncio
async def test_post_mark_applied_token_application_id_mismatch(test_app_and_session):
    client, session_maker = test_app_and_session
    app_1 = f"app-{uuid.uuid4()}"
    app_2 = f"app-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        await app_repo.create(Application(id=app_1, user_id="u1", job_id="j1"))
        await app_repo.create(Application(id=app_2, user_id="u1", job_id="j2"))
        await session.commit()

    token_1 = ActionTokenService().create_mark_applied_token(app_1, "u1")
    resp = await client.post(f"/api/applications/{app_2}/mark-applied", data={"token": token_1})
    assert resp.status_code == 403
    assert "Invalid or expired" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_post_mark_applied_missing_queue_entry_is_safe(test_app_and_session):
    """If HumanQueueEntry was never created/standalone application, mark-applied still succeeds."""
    client, session_maker = test_app_and_session
    user_id = "user_default"
    app_id = f"app-{uuid.uuid4()}"

    async with session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        await app_repo.create(Application(
            id=app_id,
            user_id=user_id,
            job_id="job-1",
            status=ApplicationStatus.PENDING_MANUAL,
        ))
        await session.commit()

    token = ActionTokenService().create_mark_applied_token(app_id, user_id)
    resp = await client.post(f"/api/applications/{app_id}/mark-applied", data={"token": token})
    assert resp.status_code == 200
    assert resp.json()["status"] == "recorded"


@pytest.mark.asyncio
async def test_queue_and_applications_api_with_custom_user_id(test_app_and_session):
    client, session_maker = test_app_and_session
    custom_user = "user_custom_456"
    q_id = f"q-{uuid.uuid4()}"
    app_id = f"app-{uuid.uuid4()}"

    async with session_maker() as session:
        queue_repo = SQLAlchemyHumanQueueRepository(session)
        app_repo = SQLAlchemyApplicationRepository(session)
        await queue_repo.enqueue(HumanQueueEntry(id=q_id, user_id=custom_user, job_id="j1"))
        await app_repo.create(Application(id=app_id, user_id=custom_user, job_id="j1"))
        await session.commit()

    # Pass X-User-ID header to test user abstraction
    resp = await client.get("/api/queue", headers={"X-User-ID": custom_user})
    assert resp.status_code == 200
    assert any(e["id"] == q_id for e in resp.json())

    resp_app = await client.get("/api/applications", headers={"X-User-ID": custom_user})
    assert resp_app.status_code == 200
    assert any(a["id"] == app_id for a in resp_app.json())


@pytest.mark.asyncio
async def test_telegram_webhook_callback(test_app_and_session):
    client, session_maker = test_app_and_session
    q1 = f"q-{uuid.uuid4()}"
    q2 = f"q-{uuid.uuid4()}"

    async with session_maker() as session:
        queue_repo = SQLAlchemyHumanQueueRepository(session)
        await queue_repo.enqueue(HumanQueueEntry(id=q1, user_id="user_default", job_id="j1"))
        await queue_repo.enqueue(HumanQueueEntry(id=q2, user_id="user_default", job_id="j2"))
        await session.commit()

    # 1. Invalid webhook token header -> 403
    payload = {"callback_query": {"data": f"approve:{q1}"}}
    resp = await client.post(
        "/api/telegram/callback",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
    )
    assert resp.status_code == 403

    # 2. Valid webhook approve callback
    resp = await client.post(
        "/api/telegram/callback",
        json=payload,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test_webhook_secret_123"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    async with session_maker() as session:
        queue_repo = SQLAlchemyHumanQueueRepository(session)
        entry1 = await queue_repo.get_by_id(q1)
        assert entry1.decision == "approved"

    # 3. Valid webhook skip callback
    payload_skip = {"callback_query": {"data": f"skip:{q2}"}}
    resp = await client.post(
        "/api/telegram/callback",
        json=payload_skip,
        headers={"X-Telegram-Bot-Api-Secret-Token": "test_webhook_secret_123"},
    )
    assert resp.status_code == 200

    async with session_maker() as session:
        queue_repo = SQLAlchemyHumanQueueRepository(session)
        entry2 = await queue_repo.get_by_id(q2)
        assert entry2.decision == "skipped"
