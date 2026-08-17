"""
tests/unit/workers/test_orchestrator.py

Unit tests for WorkflowOrchestrator v3.0.
Orchestrator subscribes to EmbeddingGenerated (not JobDiscovered).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.events.bus import InMemoryEventBus
from core.events.definitions import EmbeddingGenerated
from core.models.job import Job, JobSource, RemotePolicy
from workers.orchestrator import WorkflowOrchestrator


def _make_mock_notifier():
    """Returns an async-safe mock TelegramNotifier."""
    notifier = MagicMock()
    pending = MagicMock()
    pending.id = "tg-msg-001"
    notifier.send_approval_request = AsyncMock(return_value=pending)
    notifier.send_message = AsyncMock(return_value=None)
    return notifier


def _make_job(job_id: str = "job-test-001") -> Job:
    return Job(
        id=job_id,
        source=JobSource.GREENHOUSE,
        source_id="101",
        source_url="https://boards.greenhouse.io/acme/101",
        title="Software Engineer",
        company="Acme Corp",
        description="Python FastAPI backend role",
        skills=["Python", "FastAPI"],
        remote=RemotePolicy.REMOTE,
    )


@pytest.mark.asyncio
async def test_orchestrator_subscribes_to_embedding_generated_not_job_persisted():
    """
    INVARIANT #2: WorkflowOrchestrator must have 0 subscriptions on 'JobPersisted'.
    It subscribes to 'EmbeddingGenerated' only (plus legacy test-only JobDiscovered stub).
    """
    bus = InMemoryEventBus()
    orch = WorkflowOrchestrator(event_bus=bus)

    assert "JobPersisted" not in bus._handlers, \
        "WorkflowOrchestrator must not subscribe to JobPersisted"

    assert "EmbeddingGenerated" in bus._handlers, \
        "WorkflowOrchestrator must subscribe to EmbeddingGenerated"


@pytest.mark.asyncio
async def test_orchestrator_requires_job_repo():
    """
    WorkflowOrchestrator.handle_embedding_generated raises RuntimeError when job_repo is None.
    """
    bus = InMemoryEventBus()
    orch = WorkflowOrchestrator(event_bus=bus, job_repo=None)

    event = EmbeddingGenerated(
        entity_type="job",
        entity_id="job-001",
        model="none",
        embedding_id="",
    )
    with pytest.raises(RuntimeError, match="job_repo"):
        await orch.handle_embedding_generated(event)


@pytest.mark.asyncio
async def test_orchestrator_emits_job_ranked_for_eligible_job():
    """
    When an eligible job is fetched from job_repo, WorkflowOrchestrator emits JobRanked.
    """
    bus = InMemoryEventBus()

    job = _make_job()
    mock_job_repo = MagicMock()
    mock_job_repo.get_by_id = AsyncMock(return_value=job)

    mock_app_repo = MagicMock()
    mock_app_repo.get_by_user_and_job = AsyncMock(return_value=None)
    mock_app_repo.create = AsyncMock(return_value=job)  # _route_auto_apply may call this

    orch = WorkflowOrchestrator(
        event_bus=bus,
        job_repo=mock_job_repo,
        app_repo=mock_app_repo,
        notifier=_make_mock_notifier(),  # avoids real TelegramNotifier HTTP calls
    )

    ranked_events = []

    async def collect(e):
        ranked_events.append(e)

    bus.subscribe("JobRanked", collect)

    event = EmbeddingGenerated(
        entity_type="job",
        entity_id=job.id,
        model="none",
        embedding_id="",
    )
    await orch.handle_embedding_generated(event)

    assert len(ranked_events) >= 1, "Expected at least one JobRanked event"


@pytest.mark.asyncio
async def test_orchestrator_skips_non_job_entity_types():
    """
    EmbeddingGenerated for entity_type != 'job' must be silently skipped.
    """
    bus = InMemoryEventBus()
    mock_job_repo = MagicMock()
    mock_job_repo.get_by_id = AsyncMock(return_value=None)
    orch = WorkflowOrchestrator(event_bus=bus, job_repo=mock_job_repo)

    ranked_events = []

    async def collect(e):
        ranked_events.append(e)

    bus.subscribe("JobRanked", collect)

    event = EmbeddingGenerated(
        entity_type="user",
        entity_id="user-001",
        model="none",
        embedding_id="",
    )
    result = await orch.handle_embedding_generated(event)
    assert result == [], "Non-job entity should return empty results"
    assert ranked_events == [], "No JobRanked should be emitted for non-job entity"


@pytest.mark.asyncio
async def test_orchestrator_idempotent_skips_already_routed_job():
    """
    If app_repo returns an existing ApplicationORM for (user, job),
    the orchestrator must skip routing (idempotency guard).
    """
    bus = InMemoryEventBus()

    job = _make_job()
    mock_job_repo = MagicMock()
    mock_job_repo.get_by_id = AsyncMock(return_value=job)

    existing_app = MagicMock()
    mock_app_repo = MagicMock()
    mock_app_repo.get_by_user_and_job = AsyncMock(return_value=existing_app)

    orch = WorkflowOrchestrator(event_bus=bus, job_repo=mock_job_repo, app_repo=mock_app_repo)

    ranked_events = []

    async def collect(e):
        ranked_events.append(e)

    bus.subscribe("JobRanked", collect)

    event = EmbeddingGenerated(
        entity_type="job",
        entity_id=job.id,
        model="none",
        embedding_id="",
    )
    await orch.handle_embedding_generated(event)

    assert ranked_events == [], "Idempotency: already-routed job must not emit JobRanked"
