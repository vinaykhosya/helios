"""
tests/unit/workers/test_orchestrator.py

Unit tests for WorkflowOrchestrator event propagation.
"""
import pytest
from core.events.bus import InMemoryEventBus
from core.events.definitions import JobDiscovered
from workers.orchestrator import WorkflowOrchestrator


@pytest.mark.asyncio
async def test_workflow_orchestrator_handle_job_discovered():
    bus = InMemoryEventBus()
    orchestrator = WorkflowOrchestrator(event_bus=bus)

    published_events = []

    async def event_collector(evt):
        published_events.append(evt)

    bus.subscribe("JobRanked", event_collector)
    bus.subscribe("ApplicationSubmitted", event_collector)

    disc_event = JobDiscovered(
        job_id="job_orch_1",
        source="greenhouse",
        source_id="101",
        source_url="https://boards.greenhouse.io/acme/101",
    )

    await bus.publish(disc_event)
    assert len(published_events) >= 1

