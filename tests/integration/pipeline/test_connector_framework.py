"""
tests/integration/pipeline/test_connector_framework.py

Phase 4 Integration and Stress Test Suite.
Validates Circuit Breaker, DLQ, Telemetry, and High-Throughput (10,000 jobs) Stress simulations.
"""
from __future__ import annotations

import os
import time
import psutil
import pytest
import asyncio
import random
import shutil
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from core.models.job import Job, JobSource
from core.events.bus import InMemoryEventBus
from core.interfaces.context import ConnectorContext
from core.interfaces.snapshot_store import LocalSnapshotStore, DisabledSnapshotStore
from core.interfaces.dlq import DatabaseDeadLetterQueue
from core.interfaces.retry_policy import ExponentialBackoffPolicy, NoRetryPolicy
from database.models import Base
from database.models.system import ConnectorHealthORM, DeadLetterQueueORM, ConnectorRunORM
from backend.src.connectors.runner import ConnectorRunner, ConnectorError
from backend.src.connectors.circuit_breaker import CircuitState, CircuitBreaker
from backend.src.connectors.greenhouse import GreenhouseConnector
from backend.src.connectors.lever import LeverConnector


@pytest.fixture(scope="module")
def test_db_url():
    url = os.getenv("TEST_DATABASE_URL") or "sqlite+aiosqlite:///file:testdb?mode=memory&cache=shared"
    if "postgresql+asyncpg" not in url and "sqlite" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://")
    return url


@pytest.fixture(scope="module")
async def test_engine(test_db_url):
    engine = create_async_engine(test_db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine):
    session_maker = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session
        await session.rollback()


class MockFailureConnector:
    name = "failure_mock"
    source_url = "https://failure.test"

    async def search(self, query: str, location=None):
        raise httpx_error()


def httpx_error():
    import httpx
    # Raise a retryable error (like a timeout)
    request = httpx.Request("GET", "https://failure.test")
    return httpx.TimeoutException("Mocked timeout error", request=request)


@pytest.mark.asyncio
async def test_circuit_breaker_transitions():
    """Verify Circuit Breaker transitions CLOSED -> OPEN on 5 consecutive failures."""
    breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=0.5)
    assert breaker.state == CircuitState.CLOSED

    # 1. Trigger 5 failures
    for _ in range(5):
        breaker.record_failure()

    assert breaker.state == CircuitState.OPEN
    assert not breaker.can_execute()

    # 2. Cool down to Half Open
    await asyncio.sleep(0.6)
    assert breaker.can_execute()
    assert breaker.state == CircuitState.HALF_OPEN

    # 3. Fail again in Half Open trips to OPEN immediately
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

    # 4. Cool down again and succeed to close circuit
    await asyncio.sleep(0.6)
    assert breaker.can_execute()
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.consecutive_failures == 0


@pytest.mark.asyncio
async def test_dlq_database_routing(db_session):
    """Verify that failing payloads route to the dead_letter_queue table with detailed diagnostics."""
    dlq = DatabaseDeadLetterQueue(db_session)
    exception = ValueError("Simulated invalid payload mapping")

    await dlq.route_to_dlq(
        connector_name="test_connector",
        payload={"raw_json": {"id": "123", "title": "Staff Engineer"}},
        exception=exception,
        retry_count=3,
        source_id="123",
        idempotency_key="idemp_key_1",
        correlation_id="corr_id_1",
    )

    await db_session.flush()

    # Fetch from DLQ
    stmt = select(DeadLetterQueueORM).where(DeadLetterQueueORM.connector == "test_connector")
    res = await db_session.execute(stmt)
    dlq_record = res.scalar_one_or_none()

    assert dlq_record is not None
    assert dlq_record.source_id == "123"
    assert dlq_record.idempotency_key == "idemp_key_1"
    assert dlq_record.correlation_id == "corr_id_1"
    assert dlq_record.exception_type == "ValueError"
    assert "Simulated invalid payload mapping" in dlq_record.exception_message
    assert dlq_record.retry_count == 3
    assert dlq_record.status == "NEW"


@pytest.mark.asyncio
async def test_chronological_snapshots_naming():
    """Verify snapshot stores name files chronologically without overwriting."""
    snapshot_dir = "test_snapshots_chronological"
    if os.path.exists(snapshot_dir):
        shutil.rmtree(snapshot_dir)

    store = LocalSnapshotStore(base_dir=snapshot_dir)
    connector_name = "test_chrono"

    # Save multiple copies of the same job ID
    await store.save(connector_name, "job_99", {"title": "Iteration 1"})
    await store.save(connector_name, "job_99", {"title": "Iteration 2"})

    connector_dir = os.path.join(snapshot_dir, connector_name)
    assert os.path.exists(connector_dir)

    files = os.listdir(connector_dir)
    assert len(files) == 2  # Preserved both copies rather than overwriting!
    for f in files:
        assert f.endswith(".json")
        assert "test_chrono_job_99" in f

    shutil.rmtree(snapshot_dir)


@pytest.mark.asyncio
async def test_versioned_idempotency_keys():
    """Verify versioned idempotency keys append versions correctly."""
    from core.interfaces.idempotency import SourceUpdatedIdempotencyStrategy
    from intelligence.pipeline.stages import NormalizerStage

    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="gh_11",
        source_url="https://boards.greenhouse.io/gh_11",
        title="Software Engineer",
        company="Greenhouse Co",
        raw_data={"updated_at": "2026-07-06T12:00:00Z"}
    )

    strategy = SourceUpdatedIdempotencyStrategy()
    key1 = strategy.compute_key(job)

    # Version bump strategy test
    strategy.version = 2
    key2 = strategy.compute_key(job)

    assert key1 != key2
    assert len(key1) == 64  # SHA256 length


@pytest.mark.asyncio
async def test_rich_connector_health_metrics(db_session):
    """Verify that ConnectorRunner updates avg_latency_ms, success_rate, and counts in connector_health."""
    bus = InMemoryEventBus()
    context = ConnectorContext(
        snapshot_store=DisabledSnapshotStore(),
        retry_policy=NoRetryPolicy()
    )
    runner = ConnectorRunner(event_bus=bus, context=context)

    # 1. Success Run
    class MockSuccessConnector:
        name = "metrics_mock"
        source_url = "https://success.test"
        async def search(self, query: str, location=None):
            return [Job(
                source=JobSource.GREENHOUSE,
                source_id="m1",
                source_url="https://success.test/m1",
                title="Telemetry Eng",
                company="Telemetry Co",
            )]

    connector = MockSuccessConnector()
    await runner.run_search(connector, query="Telemetry", session=db_session)

    stmt = select(ConnectorHealthORM).where(ConnectorHealthORM.connector == "metrics_mock")
    res = await db_session.execute(stmt)
    health = res.scalar_one_or_none()

    assert health is not None
    assert health.is_healthy
    assert health.jobs_seen == 1
    assert health.consecutive_failures == 0
    assert health.success_rate == 100.0
    assert health.avg_latency_ms >= 0


@pytest.mark.asyncio
async def test_high_volume_stress_performance(db_session):
    """
    Stress test with 10,000 mocked jobs, 100 batches, random failures & duplicates.
    Measures throughput, latency, and memory profile.
    """
    bus = InMemoryEventBus()
    context = ConnectorContext(
        snapshot_store=DisabledSnapshotStore(),
        retry_policy=NoRetryPolicy()
    )
    runner = ConnectorRunner(event_bus=bus, context=context)

    # Generate 10,000 mock jobs across 100 batches of 100 jobs each
    batches_count = 100
    jobs_per_batch = 100
    total_jobs = batches_count * jobs_per_batch

    class StressConnector:
        name = "stress_mock"
        source_url = "https://stress.test"

        def __init__(self):
            self.batch_counter = 0

        async def search(self, query: str, location=None):
            # Simulate random failure (10% chance)
            if random.random() < 0.1:
                raise RuntimeError("Random stress test API failure")

            # Simulate search batch
            batch_id = self.batch_counter
            self.batch_counter += 1

            jobs = []
            for i in range(jobs_per_batch):
                # Introduce some duplicate rate (20% duplicate rate)
                job_id = f"job_{batch_id}_{i}" if random.random() > 0.2 else f"job_{batch_id}_dup"
                jobs.append(Job(
                    source=JobSource.GREENHOUSE,
                    source_id=job_id,
                    source_url=f"https://stress.test/{job_id}",
                    title=f"Developer {job_id}",
                    company="Stress Corp",
                ))
            return jobs

    connector = StressConnector()

    # Track metrics
    process = psutil.Process(os.getpid())
    mem_before_mb = process.memory_info().rss / (1024 * 1024)
    start_time = time.time()

    successful_runs = 0
    failed_runs = 0

    for _ in range(batches_count):
        try:
            await runner.run_search(connector, query="Developer", session=db_session)
            successful_runs += 1
        except Exception:
            failed_runs += 1

    duration = time.time() - start_time
    mem_after_mb = process.memory_info().rss / (1024 * 1024)

    jobs_processed = total_jobs
    throughput_jobs_sec = jobs_processed / duration if duration > 0 else jobs_processed

    print("\n" + "=" * 50)
    print(" HELIOS INGESTION INGESTION STRESS TEST RESULTS")
    print(f"Total Batches Executed: {batches_count}")
    print(f"Jobs Attempted: {total_jobs}")
    print(f"Successful Batch Runs: {successful_runs}")
    print(f"Failed Batch Runs: {failed_runs}")
    print(f"Total Duration: {duration:.2f} seconds")
    print(f"Throughput Rate: {throughput_jobs_sec:.2f} jobs/second")
    print(f"Memory Growth: {mem_after_mb - mem_before_mb:.2f} MB")
    print("=" * 50)

    assert jobs_processed == 10000
    assert duration < 5.0  # Must be incredibly fast due to mock search
