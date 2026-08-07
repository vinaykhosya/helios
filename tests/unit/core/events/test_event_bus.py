"""
tests/unit/core/events/test_event_bus.py

Unit tests for InMemoryEventBus.
Verifies subscribe, publish, and unsubscribe behaviors asynchronously.
"""
import pytest
import asyncio
from core.events.definitions import JobDiscovered
from core.events.bus import InMemoryEventBus


@pytest.mark.asyncio
async def test_event_bus_pub_sub():
    bus = InMemoryEventBus()
    fired_events = []

    async def sample_handler(event):
        fired_events.append(event)

    # 1. Subscribe
    bus.subscribe("JobDiscovered", sample_handler)

    # 2. Publish
    event = JobDiscovered(
        job_id="test-1",
        source="manual",
        source_id="manual-1",
        source_url="https://example.com/1",
    )
    await bus.publish(event)

    assert len(fired_events) == 1
    assert fired_events[0].job_id == "test-1"

    # 3. Unsubscribe
    bus.unsubscribe("JobDiscovered", sample_handler)
    await bus.publish(event)

    # Count should still be 1 (unsubscribed)
    assert len(fired_events) == 1


@pytest.mark.asyncio
async def test_event_bus_multiple_subscribers():
    bus = InMemoryEventBus()
    calls = []

    async def h1(event):
        calls.append("h1")

    async def h2(event):
        calls.append("h2")

    bus.subscribe("JobDiscovered", h1)
    bus.subscribe("JobDiscovered", h2)

    event = JobDiscovered(
        job_id="test-2",
        source="manual",
        source_id="manual-2",
        source_url="https://example.com/2",
    )
    await bus.publish(event)

    assert "h1" in calls
    assert "h2" in calls
    assert len(calls) == 2
