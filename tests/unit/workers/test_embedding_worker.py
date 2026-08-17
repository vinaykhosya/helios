"""
tests/unit/workers/test_embedding_worker.py

Unit tests for EmbeddingWorker.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.events.bus import InMemoryEventBus
from core.events.definitions import JobPersisted, EmbeddingGenerated
from workers.embedding_worker import EmbeddingWorker


@pytest.mark.asyncio
async def test_embedding_worker_subscribes_to_job_persisted_only():
    """
    INVARIANT #2 (EmbeddingWorker side):
    EmbeddingWorker must subscribe to 'JobPersisted' and NOT to 'JobDiscovered'.
    """
    bus = InMemoryEventBus()
    worker = EmbeddingWorker(event_bus=bus)

    assert "JobPersisted" in bus._handlers, \
        "EmbeddingWorker must subscribe to JobPersisted"
    assert "JobDiscovered" not in bus._handlers, \
        "EmbeddingWorker must NOT subscribe to JobDiscovered"


@pytest.mark.asyncio
async def test_embedding_worker_emits_embedding_generated_without_provider():
    """
    With no embedding_provider, EmbeddingWorker must still emit EmbeddingGenerated
    with embedding_id="" (semantic fallback signal).
    """
    bus = InMemoryEventBus()
    worker = EmbeddingWorker(event_bus=bus, embedding_provider=None)

    received = []

    async def collect(e):
        received.append(e)

    bus.subscribe("EmbeddingGenerated", collect)

    event = JobPersisted(
        job_id="job-001",
        source="greenhouse",
        source_url="https://example.com/job/1",
    )
    await worker.handle_job_persisted(event)

    assert len(received) == 1
    eg: EmbeddingGenerated = received[0]
    assert eg.entity_type == "job"
    assert eg.entity_id == "job-001"
    assert eg.embedding_id == "", "No provider -> embedding_id must be empty string"


@pytest.mark.asyncio
async def test_embedding_worker_emits_embedding_generated_with_real_id_when_provider_wired():
    """
    With a real embedding provider and job_repo, EmbeddingWorker emits
    EmbeddingGenerated with a non-empty embedding_id UUID.
    """
    bus = InMemoryEventBus()

    mock_provider = MagicMock()
    mock_provider.model_name = "test-model"
    mock_provider.embed = AsyncMock(return_value=[[0.1] * 384])

    mock_job = MagicMock()
    mock_job.title = "Software Engineer"
    mock_job.company = "Acme"
    mock_job.description = "Python role"
    mock_job_repo = MagicMock()
    mock_job_repo.get_by_id = AsyncMock(return_value=mock_job)

    worker = EmbeddingWorker(
        event_bus=bus,
        embedding_provider=mock_provider,
        job_repo=mock_job_repo,
    )

    received = []

    async def collect(e):
        received.append(e)

    bus.subscribe("EmbeddingGenerated", collect)

    event = JobPersisted(
        job_id="job-002",
        source="lever",
        source_url="https://jobs.lever.co/acme/123",
    )
    await worker.handle_job_persisted(event)

    assert len(received) == 1
    eg: EmbeddingGenerated = received[0]
    assert eg.embedding_id != "", "Provider wired -> embedding_id must be a real UUID"
    assert eg.entity_id == "job-002"


@pytest.mark.asyncio
async def test_embedding_worker_emits_empty_id_on_provider_failure():
    """
    If the embedding provider raises, EmbeddingWorker must still emit EmbeddingGenerated
    with embedding_id="" and NOT re-raise. Pipeline must not crash.
    """
    bus = InMemoryEventBus()

    bad_provider = MagicMock()
    bad_provider.model_name = "failing-model"
    bad_provider.embed = AsyncMock(side_effect=RuntimeError("GPU OOM"))

    worker = EmbeddingWorker(event_bus=bus, embedding_provider=bad_provider)

    received = []

    async def collect(e):
        received.append(e)

    bus.subscribe("EmbeddingGenerated", collect)

    event = JobPersisted(
        job_id="job-003",
        source="workday",
        source_url="https://workday.com/job/3",
    )
    await worker.handle_job_persisted(event)

    assert len(received) == 1
    assert received[0].embedding_id == "", "Failure -> embedding_id must be empty string"
