"""
tests/unit/core/models/test_human_queue_entry.py

Unit tests for HumanQueueEntry domain model and state machine transitions.
"""
import pytest
from core.models.human_queue import HumanQueueEntry


def make():
    return HumanQueueEntry(user_id="u1", job_id="j1")


def test_approve():
    assert make().transition_to("approved").decision == "approved"


def test_skip():
    assert make().transition_to("skipped").decision == "skipped"


def test_complete():
    """pending -> completed is valid (direct mark-applied path)."""
    assert make().transition_to("completed").decision == "completed"


def test_approved_to_completed():
    """approved -> completed is valid (approved in Telegram then marked applied)."""
    appr = make().transition_to("approved")
    done = appr.transition_to("completed")
    assert done.decision == "completed"


def test_skipped_to_approved_raises():
    with pytest.raises(ValueError, match="Invalid state transition"):
        make().transition_to("skipped").transition_to("approved")


def test_skipped_to_completed_raises():
    """Terminal skipped cannot transition to completed."""
    with pytest.raises(ValueError, match="Invalid state transition"):
        make().transition_to("skipped").transition_to("completed")


def test_expired_to_completed_raises():
    """Terminal expired cannot transition to completed."""
    with pytest.raises(ValueError, match="Invalid state transition"):
        make().transition_to("expired").transition_to("completed")


def test_terminal_state_raises():
    done = make().transition_to("completed")
    with pytest.raises(ValueError, match="terminal state"):
        done.transition_to("pending")


def test_pending_to_pending_raises():
    """Critical fix: pending -> pending must fail."""
    with pytest.raises(ValueError, match="Invalid state transition"):
        make().transition_to("pending")


def test_expires_at_is_48h():
    e = make()
    delta = (e.expires_at - e.created_at).total_seconds()
    assert 47 * 3600 < delta <= 49 * 3600


def test_transition_immutable():
    """transition_to() must not mutate the original instance."""
    e = make()
    approved = e.transition_to("approved")
    assert e.decision == "pending"    # original unchanged
    assert approved.decision == "approved"


def test_set_telegram_pending_id_does_not_need_state_transition():
    """
    Regression test: updating telegram_pending_id is a metadata change, not a state change.
    """
    e = make()
    e2 = e.model_copy(update={"telegram_pending_id": "tg-abc-123"})
    assert e2.decision == "pending"   # state unchanged
    assert e2.telegram_pending_id == "tg-abc-123"
