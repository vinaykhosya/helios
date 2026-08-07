"""
tests/unit/core/events/test_events.py

Unit tests for Helios event contracts.

Verifies:
- All events carry the 5 base fields
- event_type is auto-derived from the class name
- correlation_id propagation pattern
- Child events can inherit parent's correlation_id
"""
import pytest
from core.events.definitions import (
    JobDiscovered, JobRanked, ConnectorRunFailed,
    ApplicationStatusChanged, NotificationRequested,
)


class TestBaseEventFields:
    def test_all_base_fields_present(self):
        event = JobDiscovered(
            job_id="j1", source="jobindex", source_id="s1", source_url="https://example.com"
        )
        assert event.event_id
        assert event.event_type == "JobDiscovered"
        assert event.occurred_at is not None
        assert event.correlation_id
        assert isinstance(event.metadata, dict)

    def test_event_type_auto_derived(self):
        e1 = ConnectorRunFailed(connector="jobindex", run_id="r1", error="timeout")
        e2 = ApplicationStatusChanged(app_id="a1", user_id="u1", job_id="j1", old_status="saved", new_status="applied")
        assert e1.event_type == "ConnectorRunFailed"
        assert e2.event_type == "ApplicationStatusChanged"

    def test_correlation_id_is_unique_by_default(self):
        e1 = JobDiscovered(job_id="j1", source="x", source_id="s1", source_url="u")
        e2 = JobDiscovered(job_id="j2", source="x", source_id="s2", source_url="u")
        assert e1.correlation_id != e2.correlation_id


class TestCorrelationIdPropagation:
    def test_child_event_propagates_parent_correlation_id(self):
        """
        Workers MUST propagate the parent correlation_id.
        This test documents the expected pattern.
        """
        parent = ConnectorRunFailed(connector="jobindex", run_id="r1", error="429")
        child = JobDiscovered(
            job_id="j1",
            source="jobindex",
            source_id="s1",
            source_url="https://jobindex.dk/job/s1",
            correlation_id=parent.correlation_id,   # propagated
        )
        assert child.correlation_id == parent.correlation_id

    def test_event_id_differs_from_correlation_id(self):
        """event_id = this specific event; correlation_id = the chain it belongs to."""
        event = JobRanked(job_id="j1", user_id="u1", fit_score=0.87)
        assert event.event_id != event.correlation_id

    def test_metadata_accepts_arbitrary_context(self):
        event = NotificationRequested(
            user_id="u1",
            type="new_match",
            title="New job: Senior Engineer",
            body="Fit score: 0.92",
            metadata={"connector": "jobindex", "run_id": "r1"},
        )
        assert event.metadata["connector"] == "jobindex"
