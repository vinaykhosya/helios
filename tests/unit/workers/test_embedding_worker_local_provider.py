"""
tests/unit/workers/test_embedding_worker_local_provider.py

Integration test for EmbeddingWorker wired with LocalEmbeddingProvider.
"""
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from core.events.definitions import JobPersisted, EmbeddingGenerated
from core.models.job import Job, JobSource
from intelligence.embeddings.provider import LocalEmbeddingProvider
from workers.embedding_worker import EmbeddingWorker


class RecordingBus:
    def __init__(self):
        self.handlers = {}
        self.published = []

    def subscribe(self, event_type: str, handler):
        self.handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event):
        self.published.append(event)


@pytest.mark.asyncio
async def test_embedding_worker_with_local_provider_emits_valid_embedding_uuid():
    bus = RecordingBus()
    provider = LocalEmbeddingProvider()

    mock_job = Job(
        id="job-embed-123",
        source=JobSource.LINKEDIN,
        source_id="linkedin-999",
        source_url="https://linkedin.com/jobs/view/999",
        title="Senior Python Backend Developer",
        company="Acme Corp",
        description="We are seeking an expert FastAPI / Python backend developer.",
    )
    job_repo = MagicMock()
    job_repo.get_by_id = AsyncMock(return_value=mock_job)

    worker = EmbeddingWorker(
        event_bus=bus,
        embedding_provider=provider,
        job_repo=job_repo,
    )

    event = JobPersisted(
        job_id="job-embed-123",
        source="linkedin",
        source_url="https://linkedin.com/jobs/view/999",
        correlation_id="corr-xyz",
    )

    await worker.handle_job_persisted(event)

    assert len(bus.published) == 1
    emitted = bus.published[0]
    assert isinstance(emitted, EmbeddingGenerated)
    assert emitted.entity_id == "job-embed-123"
    assert emitted.model == "sentence-transformers/all-MiniLM-L6-v2"
    assert emitted.embedding_id != ""
    # Verify embedding_id is a valid UUID
    uuid_obj = uuid.UUID(emitted.embedding_id)
    assert str(uuid_obj) == emitted.embedding_id
