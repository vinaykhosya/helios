"""
core/models/application.py

Application model. Replaces job_search_tracker.csv.
Tracks the full lifecycle of a user's job application.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ApplicationStatus(str, Enum):
    """
    Ordered application lifecycle states.

    Human Queue path (ASK_USER routing):
      PENDING_MANUAL    — job routed to Human Queue; no application submitted yet.
                          ApplicationORM exists. HumanQueueORM exists. User has not applied.
      SUBMITTED_MANUAL  — user manually applied and confirmed via /mark-applied.
                          applied_at is set. HumanQueueORM.decision = completed.

    Automation path (AUTO_APPLY routing):
      AUTOMATION_QUEUED — queued for Playwright automation.
                          ApplicationORM exists. Playwright has NOT yet run.
                          INVARIANT: ApplicationSubmitted is NEVER emitted at this status.
                          Only emitted after Playwright verifies submission evidence (Phase 5).

    Shared outcome states (set by EmailApplicationMatcher, Gmail tracker, user):
      APPLIED, PHONE_SCREEN, TECHNICAL, CASE, FINAL, OFFER, etc.

    Transitions are enforced by ApplicationService.
    """
    # ─ Human Queue path ────────────────────────────────────────────────────
    PENDING_MANUAL = "pending_manual"
    SUBMITTED_MANUAL = "submitted_manual"

    # ─ Automation path ───────────────────────────────────────────────────
    AUTOMATION_QUEUED = "automation_queued"

    # ─ Legacy / shared outcome states ─────────────────────────────────────
    SAVED = "saved"
    APPLIED = "applied"
    PHONE_SCREEN = "phone_screen"
    TECHNICAL = "technical"
    CASE = "case"
    FINAL = "final"
    OFFER = "offer"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    NO_RESPONSE = "no_response"


class Application(BaseModel):
    """
    Job application record.

    Created when a user decides to track or apply for a job.
    Updated as the application progresses through stages.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = Field(default=1)
    user_id: str
    job_id: str

    # ── Status ────────────────────────────────────────────────────────────────
    status: ApplicationStatus = ApplicationStatus.SAVED
    applied_at: Optional[datetime] = None

    # ── Documents ─────────────────────────────────────────────────────────────
    resume_id: Optional[str] = None            # FK to resumes table
    cover_letter_id: Optional[str] = None      # FK to cover_letters table

    # ── Assessment ────────────────────────────────────────────────────────────
    fit_rating: Optional[float] = None         # 0.0–1.0, set during /apply evaluation
    notes: Optional[str] = None

    # ── Context ───────────────────────────────────────────────────────────────
    contact_person: Optional[str] = None
    source_channel: Optional[str] = None       # how the job was found
    interview_session_ids: list[str] = Field(default_factory=list)

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}
