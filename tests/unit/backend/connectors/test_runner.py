"""
tests/unit/backend/connectors/test_runner.py

Unit tests for ConnectorRunner.
Uses mock connectors and event buses to verify retries, timeouts, and event publishing.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from backend.src.connectors.runner import ConnectorRunner
from core.events.bus import InMemoryEventBus
from core.models.job import Job, JobSource


class DummyConnector:
    name = "dummy"
    source_url = "https://dummy.helios.test"

    def __init__(self, jobs=None, should_fail=False, should_timeout=False):
        self._jobs = jobs or []
        self._should_fail = should_fail
        self._should_timeout = should_timeout

    async def search(self, query: str, location=None):
        if self._should_fail:
            raise RuntimeError("Database error")
        if self._should_timeout:
            await asyncio.sleep(5.0)  # long sleep to trigger timeout
        return self._jobs


@pytest.mark.asyncio
async def test_runner_successful_run():
    bus = InMemoryEventBus()
    runner = ConnectorRunner(event_bus=bus, timeout_seconds=1.0, max_retries=2)

    job1 = Job(
        source=JobSource.GREENHOUSE,
        source_id="d1",
        source_url="https://example.com/d1",
        title="Python Dev",
        company="Dummy Co",
    )
    connector = DummyConnector(jobs=[job1])

    fired_events = []
    async def track_events(e):
        fired_events.append(e)

    bus.subscribe("ConnectorRunStarted", track_events)
    bus.subscribe("ConnectorRunCompleted", track_events)
    bus.subscribe("JobDiscovered", track_events)

    events_published = await runner.run_search(connector, query="Python")

    assert len(events_published) == 1
    assert len(fired_events) == 3  # started, completed, job_discovered
    assert fired_events[0].event_type == "ConnectorRunStarted"
    assert fired_events[1].event_type == "ConnectorRunCompleted"
    assert fired_events[2].event_type == "JobDiscovered"
    assert fired_events[2].job_id == job1.id


@pytest.mark.asyncio
async def test_runner_failure_run_retries():
    bus = InMemoryEventBus()
    # 0.05s timeout, 2 retries, no wait backoff for fast tests
    runner = ConnectorRunner(event_bus=bus, timeout_seconds=0.1, max_retries=2)
    connector = DummyConnector(should_fail=True)

    fired_events = []
    async def track_events(e):
        fired_events.append(e)

    bus.subscribe("ConnectorRunFailed", track_events)

    await runner.run_search(connector, query="Python")

    # Should attempt twice and publish ConnectorRunFailed event
    assert len(fired_events) == 1
    assert fired_events[0].event_type == "ConnectorRunFailed"
    assert "Database error" in fired_events[0].error
