"""
core/models/human_queue.py

HumanQueueEntry domain model.
State machine is enforced in Python before any DB write.
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field


VALID_TRANSITIONS: dict[str, set[str]] = {
    "pending":   {"approved", "skipped", "expired", "completed"},
    "approved":  {"executing", "completed"},
    "executing": {"completed", "failed"},
    "completed": set(),   # terminal
    "skipped":   set(),   # terminal
    "expired":   set(),   # terminal
    "failed":    set(),   # terminal
}


class HumanQueueEntry(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    job_id: str
    application_id: Optional[str] = None

    # Telegram metadata (NOT state machine — updated via set_telegram_pending_id())
    telegram_pending_id: Optional[str] = None
    telegram_message_id: Optional[str] = None

    decision: str = "pending"

    fit_score: Optional[float] = None
    confidence_score: Optional[float] = None
    friction_score: int = 0
    routing_reason: Optional[str] = None

    resume_path: Optional[str] = None
    application_url: Optional[str] = None
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None
    expires_at: Optional[datetime] = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=48)
    )
    sheets_row_synced: bool = False

    def transition_to(self, new_decision: str) -> "HumanQueueEntry":
        """
        Validate and apply state transition.
        Raises ValueError on invalid transitions — including pending → pending.
        Returns a NEW instance (original is unchanged — domain objects are immutable).
        """
        allowed = VALID_TRANSITIONS.get(self.decision, set())
        if new_decision not in allowed:
            raise ValueError(
                f"Invalid state transition: '{self.decision}' → '{new_decision}'. "
                f"Allowed from '{self.decision}': "
                f"{sorted(allowed) if allowed else 'none (terminal state)'}"
            )
        update: dict = {"decision": new_decision}
        if new_decision in {"approved", "skipped", "expired", "completed"}:
            update["decided_at"] = datetime.utcnow()
        return self.model_copy(update=update)

    def set_telegram_pending_id(self, pending_id: str) -> "HumanQueueEntry":
        """
        Records the Telegram message ID for this entry.
        This is METADATA -- it does NOT change the state machine.
        """
        self.telegram_pending_id = pending_id
        return self

    model_config = {"use_enum_values": True}
