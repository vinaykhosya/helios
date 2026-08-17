"""
tests/unit/repositories/test_human_queue_repository.py

Unit tests for SQLAlchemyHumanQueueRepository.
Uses in-memory SQLite async engine with schema translation.
"""
import pytest
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

from core.models.human_queue import HumanQueueEntry
from database.models.base import Base
from database.models.human_queue import HumanQueueORM
from backend.src.repositories.human_queue import SQLAlchemyHumanQueueRepository


@pytest.fixture
async def db_session():
    """Provides a fresh isolated SQLite in-memory async session."""
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
    async with session_maker() as session:
        yield session

    await engine.dispose()


def _make_entry(entry_id=None, application_id=None, decision="pending", user_id="u1", job_id="j1"):
    return HumanQueueEntry(
        id=entry_id or str(uuid.uuid4()),
        user_id=user_id,
        job_id=job_id,
        application_id=application_id or str(uuid.uuid4()),
        decision=decision,
        fit_score=0.85,
        confidence_score=0.90,
        friction_score=2,
        routing_reason="85% match",
        matching_skills=["Python", "FastAPI"],
        missing_skills=["Docker"],
    )


@pytest.mark.asyncio
async def test_enqueue_and_get_by_id(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    entry = _make_entry()

    saved = await repo.enqueue(entry)
    await db_session.commit()

    assert saved.id == entry.id
    assert saved.decision == "pending"

    fetched = await repo.get_by_id(entry.id)
    assert fetched is not None
    assert fetched.id == entry.id
    assert fetched.application_id == entry.application_id
    assert fetched.fit_score == 0.85
    assert fetched.missing_skills == ["Docker"]


@pytest.mark.asyncio
async def test_enqueue_non_pending_raises(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    entry = _make_entry(decision="approved")
    with pytest.raises(ValueError, match="enqueue.*requires decision='pending'"):
        await repo.enqueue(entry)


@pytest.mark.asyncio
async def test_decide_transitions_state(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    entry = await repo.enqueue(_make_entry())
    await db_session.commit()

    # pending -> approved
    approved = await repo.decide(entry.id, "approved")
    await db_session.commit()
    assert approved.decision == "approved"
    assert approved.decided_at is not None

    # approved -> completed
    completed = await repo.decide(entry.id, "completed")
    await db_session.commit()
    assert completed.decision == "completed"


@pytest.mark.asyncio
async def test_decide_invalid_transition_raises_and_preserves_state(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    entry = await repo.enqueue(_make_entry())
    await db_session.commit()

    # pending -> skipped
    await repo.decide(entry.id, "skipped")
    await db_session.commit()

    # skipped -> approved (invalid transition from terminal skipped)
    with pytest.raises(ValueError, match="Invalid state transition"):
        await repo.decide(entry.id, "approved")

    # verify state is still skipped in DB
    current = await repo.get_by_id(entry.id)
    assert current.decision == "skipped"


@pytest.mark.asyncio
async def test_set_telegram_pending_id_updates_metadata_without_state_transition(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    entry = await repo.enqueue(_make_entry())
    await db_session.commit()

    updated = await repo.set_telegram_pending_id(entry.id, "tg-msg-456")
    await db_session.commit()

    assert updated.decision == "pending"   # decision must NOT change
    assert updated.telegram_pending_id == "tg-msg-456"

    fetched = await repo.get_by_telegram_pending_id("tg-msg-456")
    assert fetched is not None
    assert fetched.id == entry.id


@pytest.mark.asyncio
async def test_get_by_application_id(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    app_id = "app-target-789"
    entry = await repo.enqueue(_make_entry(application_id=app_id))
    await db_session.commit()

    fetched = await repo.get_by_application_id(app_id)
    assert fetched is not None
    assert fetched.id == entry.id
    assert fetched.application_id == app_id


@pytest.mark.asyncio
async def test_mark_sheets_synced(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    entry = await repo.enqueue(_make_entry())
    await db_session.commit()

    assert entry.sheets_row_synced is False

    await repo.mark_sheets_synced(entry.id)
    await db_session.commit()

    fetched = await repo.get_by_id(entry.id)
    assert fetched.sheets_row_synced is True


@pytest.mark.asyncio
async def test_get_pending_and_list_all(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    e1 = await repo.enqueue(_make_entry(user_id="user_test"))
    e2 = await repo.enqueue(_make_entry(user_id="user_test"))
    await repo.decide(e2.id, "approved")
    await db_session.commit()

    pending = await repo.get_pending("user_test")
    assert len(pending) == 1
    assert pending[0].id == e1.id

    all_entries = await repo.list_all("user_test")
    assert len(all_entries) == 2

    only_approved = await repo.list_all("user_test", decision="approved")
    assert len(only_approved) == 1
    assert only_approved[0].id == e2.id


@pytest.mark.asyncio
async def test_expire_stale(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    entry = _make_entry()
    # artificially set created_at to 50 hours ago
    entry.created_at = datetime.utcnow() - timedelta(hours=50)
    await repo.enqueue(entry)
    await db_session.commit()

    expired_count = await repo.expire_stale(ttl_hours=48)
    await db_session.commit()

    assert expired_count == 1
    fetched = await repo.get_by_id(entry.id)
    assert fetched.decision == "expired"


@pytest.mark.asyncio
async def test_nonexistent_entry_raises_lookup_error(db_session):
    repo = SQLAlchemyHumanQueueRepository(db_session)
    with pytest.raises(LookupError, match="not found"):
        await repo.decide("non-existent-id", "approved")
