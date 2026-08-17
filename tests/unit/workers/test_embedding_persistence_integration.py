"""
tests/unit/workers/test_embedding_persistence_integration.py

Integration test proving that EmbeddingWorker + LocalEmbeddingProvider persists
real 384-dimensional vectors to the database via SQLAlchemyEmbeddingRepository.
"""
import math
import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.events.definitions import JobPersisted, EmbeddingGenerated
from core.models.job import Job, JobSource
from database.models.base import Base
from backend.src.repositories.job import SQLAlchemyJobRepository
from backend.src.repositories.embedding import SQLAlchemyEmbeddingRepository
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


@pytest.fixture
async def db_session():
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


@pytest.mark.asyncio
async def test_embedding_worker_persists_real_384d_vector_to_database(db_session):
    job_repo = SQLAlchemyJobRepository(db_session)
    embedding_repo = SQLAlchemyEmbeddingRepository(db_session)
    provider = LocalEmbeddingProvider()
    bus = RecordingBus()

    # 1. Create and persist a real job in DB
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        source=JobSource.LINKEDIN,
        source_id="job-persisted-123",
        source_url="https://linkedin.com/jobs/view/123",
        title="Staff Backend Systems Architect",
        company="Uber Technologies",
        description="Design and build high-throughput distributed systems using Python and Rust.",
    )
    await job_repo.create(job)
    await db_session.commit()

    # 2. Instantiate EmbeddingWorker with real database embedding_repo and LocalEmbeddingProvider
    worker = EmbeddingWorker(
        event_bus=bus,
        embedding_provider=provider,
        job_repo=job_repo,
        embedding_repo=embedding_repo,
    )

    # 3. Simulate JobPersisted event
    event = JobPersisted(
        job_id=job_id,
        source="linkedin",
        source_url="https://linkedin.com/jobs/view/123",
        correlation_id="corr-persisted-test",
    )
    await worker.handle_job_persisted(event)
    await db_session.commit()

    # 4. Verify EmbeddingGenerated was emitted
    assert len(bus.published) == 1
    emitted = bus.published[0]
    assert isinstance(emitted, EmbeddingGenerated)
    assert emitted.entity_id == job_id
    assert emitted.embedding_id != ""

    # 5. Retrieve the stored embedding directly from database
    stored = await embedding_repo.get_by_id(emitted.embedding_id)
    assert stored is not None
    assert stored["id"] == emitted.embedding_id
    assert stored["job_id"] == job_id
    assert stored["model"] == "sentence-transformers/all-MiniLM-L6-v2"

    vector = stored["vector"]
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(v, float) and math.isfinite(v) for v in vector)

    # Verify L2 normalization
    norm = math.sqrt(sum(x * x for x in vector))
    assert 0.98 <= norm <= 1.02

    # Verify retrieval by job_id works
    stored_by_job = await embedding_repo.get_by_job_id(job_id)
    assert stored_by_job is not None
    assert stored_by_job["id"] == emitted.embedding_id
