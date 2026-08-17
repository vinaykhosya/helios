"""
tests/unit/workers/test_orchestrator_human_queue_atomic.py

Integration tests for WorkflowOrchestrator atomic routing into Human Queue (Invariant #9).
Verifies:
  1. ApplicationORM + HumanQueueORM created atomically with application_id populated.
"""
import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.events.bus import InMemoryEventBus
from core.events.definitions import EmbeddingGenerated
from core.models.job import Job, JobSource, RemotePolicy
from core.models.application import ApplicationStatus
from automation.confidence import ApplicationDecision
from database.models.base import Base
from backend.src.repositories.application import SQLAlchemyApplicationRepository
from backend.src.repositories.human_queue import SQLAlchemyHumanQueueRepository
from workers.orchestrator import WorkflowOrchestrator


@pytest.fixture
async def db_session_maker():
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
    yield session_maker
    await engine.dispose()


def _make_job(job_id: str = "job-atomic-1") -> Job:
    return Job(
        id=job_id,
        source=JobSource.GREENHOUSE,
        source_id="gh-101",
        source_url="https://boards.greenhouse.io/acme/101",
        title="Senior Python Backend Engineer",
        company="Acme Corp",
        description="FastAPI, PostgreSQL, Redis, Kubernetes required.",
        skills=["Python", "FastAPI"],
        remote=RemotePolicy.REMOTE,
    )


@pytest.mark.asyncio
async def test_route_human_queue_atomic_success(db_session_maker):
    """
    Verifies that when _route_human_queue runs with real repositories:
      - ApplicationORM is created with status PENDING_MANUAL
      - HumanQueueORM is created referencing application.id (Invariant #6)
      - Both are committed together.
    """
    bus = InMemoryEventBus()
    job = _make_job()

    mock_job_repo = MagicMock()
    mock_job_repo.get_by_id = AsyncMock(return_value=job)

    async with db_session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        queue_repo = SQLAlchemyHumanQueueRepository(session)

        mock_notifier = MagicMock()
        pending = MagicMock()
        pending.id = "tg-pending-999"
        mock_notifier.send_approval_request = AsyncMock(return_value=pending)
        mock_notifier.send_message = AsyncMock(return_value=None)

        orch = WorkflowOrchestrator(
            event_bus=bus,
            job_repo=mock_job_repo,
            app_repo=app_repo,
            queue_repo=queue_repo,
            notifier=mock_notifier,
        )

        mock_engine = MagicMock()
        mock_engine.decide.return_value = ApplicationDecision.ASK_USER
        orch.confidence_engine = mock_engine

        event = EmbeddingGenerated(
            entity_type="job",
            entity_id=job.id,
            model="none",
            embedding_id="",
        )
        await orch.handle_embedding_generated(event)

    # Verify both records exist in DB and point to each other
    async with db_session_maker() as session:
        app_repo = SQLAlchemyApplicationRepository(session)
        queue_repo = SQLAlchemyHumanQueueRepository(session)

        app = await app_repo.get_by_user_and_job("user_default", job.id)
        assert app is not None
        assert app.status == ApplicationStatus.PENDING_MANUAL

        entry = await queue_repo.get_by_application_id(app.id)
        assert entry is not None
        assert entry.job_id == job.id
        assert entry.application_id == app.id
        assert entry.decision == "pending"
        assert entry.telegram_pending_id == "tg-pending-999"
