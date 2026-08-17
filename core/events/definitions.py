"""
core/events/definitions.py

All Helios event contracts.

Events are the communication layer between workers.
Workers subscribe to event types and react asynchronously.
No worker calls another worker directly.

Event naming convention: <Entity><PastTenseVerb>
  Good: JobDiscovered, ApplicationStatusChanged, ConnectorRunFailed
  Bad:  DiscoverJob, JobEvent, Event1

Base fields on every event:
  event_id       — unique ID for this specific event instance
  event_type     — derived from class name; allows filtering without isinstance()
  occurred_at    — UTC timestamp of when the event was produced
  correlation_id — groups related events across a pipeline run or request.
                   Workers that emit child events should propagate the parent's
                   correlation_id so the full chain is traceable in audit_logs.
  metadata       — arbitrary key-value pairs for context (connector name, etc.)

Phases:
  Phase 1: These contracts only — no bus implementation.
  Phase 2: Redis Streams or similar pub/sub backing.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class HeliosEvent(BaseModel):
    """Base class for all Helios events."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str = Field(default="")        # auto-set by model_validator below
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    """Groups related events across a pipeline run or request.
    Workers emitting child events MUST propagate the parent's correlation_id."""
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def set_event_type(self) -> "HeliosEvent":
        if not self.event_type:
            self.event_type = type(self).__name__
        return self


# ── Job Lifecycle ─────────────────────────────────────────────────────────────

class JobDiscovered(HeliosEvent):
    """
    Fired when a connector finds a job not previously seen in the database.
    Subscribers: RankingWorker, EmbeddingWorker.
    """
    job_id: str
    source: str
    source_id: str
    source_url: str


class JobPersisted(HeliosEvent):
    """
    Fired by IngestionWorker AFTER the job row is committed to the database.
    At this point, job.id is a REAL UUID that exists in the jobs table.

    INVARIANT: This event is emitted post-persistence, never pre-persistence.
    EmbeddingWorker subscribes here. WorkflowOrchestrator does NOT subscribe here.
    Subscribers: EmbeddingWorker ONLY.
    """
    job_id: str       # real DB UUID
    source: str
    source_url: str


class JobUpdated(HeliosEvent):
    """
    Fired when an existing job's fields change (title, deadline, salary, status).
    Subscribers: NotificationWorker (deadline changes), EmbeddingWorker (content changes).
    """
    job_id: str
    changes: dict[str, Any]   # {field_name: new_value}


class JobExpired(HeliosEvent):
    """
    Fired when a job's deadline passes or it is removed from the portal.
    Subscribers: NotificationWorker (notify users who saved the job).
    """
    job_id: str
    reason: str   # "deadline_passed" | "removed_by_portal" | "manual"


class JobRanked(HeliosEvent):
    """
    Fired after RankerStage assigns a fit_score to a job for a specific user.
    Subscribers: NotificationWorker (if score ≥ user threshold).
    """
    job_id: str
    user_id: str
    fit_score: float   # 0.0–1.0


# ── Application Lifecycle ─────────────────────────────────────────────────────

class ApplicationCreated(HeliosEvent):
    """
    Fired when a user creates a new application record.
    Subscribers: NotificationWorker, AnalyticsWorker.
    """
    app_id: str
    user_id: str
    job_id: str
    status: str   # initial status, typically "saved" or "applied"


class ApplicationStatusChanged(HeliosEvent):
    """
    Fired when an application moves to a new status.
    Subscribers: NotificationWorker, AnalyticsWorker.
    """
    app_id: str
    user_id: str
    job_id: str
    old_status: str
    new_status: str


class ApplicationSubmitted(HeliosEvent):
    """
    Fired when an application form is verified as submitted by Playwright evidence.

    INVARIANT (Invariant #1): This event may ONLY be emitted after:
      1. Playwright successfully submitted the form, AND
      2. Evidence of submission exists (confirmation page, confirmation_id, screenshot).
    It is NEVER emitted merely because:
      - routing decision is AUTO_APPLY, or
      - ApplicationORM(AUTOMATION_QUEUED) was created, or
      - a user approved an application in Telegram.
    Violation of this invariant is a critical data integrity bug.

    Subscribers: MemoryService, NotificationWorker, MetricsWorker.
    """
    app_id: str
    user_id: str
    job_id: str
    source: str
    confirmation_id: Optional[str] = None
    confidence_score: float = 1.0
    resume_version: Optional[str] = None


class ApplicationFailed(HeliosEvent):
    """
    Fired when an application attempt fails or errors out.
    Subscribers: RecoveryEngine, DeadLetterQueue, MonitoringWorker.
    """
    app_id: str
    user_id: str
    job_id: str
    source: str
    error: str
    dom_snapshot_path: Optional[str] = None


class HumanApprovalRequested(HeliosEvent):
    """
    Fired when automation pauses for human verification, CAPTCHA, or custom questions.
    Subscribers: TelegramNotifier, MobilePushWorker.
    """
    pending_id: str
    job_id: str
    user_id: str
    pause_reason: str
    confidence_score: float


class HumanApprovalGranted(HeliosEvent):
    """
    Fired when a human approves an application request (e.g., via Telegram inline button).
    Subscribers: WorkflowOrchestrator (to resume Playwright automation).
    """
    pending_id: str
    job_id: str
    user_id: str
    application_id: str


class ApplicationManuallySubmitted(HeliosEvent):
    """
    Fired when a user confirms they have manually submitted an application via
    the /mark-applied endpoint (POST, after confirming via the GET page).

    This is distinct from ApplicationSubmitted — no Playwright evidence is required.
    It records a user's self-reported action.
    Subscribers: MemoryService, NotificationWorker, GoogleSheetsSyncService.
    """
    app_id: str
    user_id: str
    job_id: str
    applied_at: datetime


class ApplicationPreparationFailed(HeliosEvent):
    """
    Fired when the pipeline fails to prepare or route an application
    (e.g., eligibility gate failed, friction scorer errored, routing exception).
    Subscribers: DeadLetterQueue, MonitoringWorker.
    """
    job_id: str
    user_id: str
    reason: str
    stage: str    # e.g. "eligibility_gate", "ranking", "routing"

# ── Connector / Pipeline Lifecycle ────────────────────────────────────────────

class ConnectorRunStarted(HeliosEvent):
    """
    Fired when a connector begins a search run.
    Subscribers: MonitoringWorker.
    """
    connector: str
    trigger: str   # "scheduled" | "manual" | "webhook"
    run_id: str


class ConnectorRunCompleted(HeliosEvent):
    """
    Fired when a connector run finishes successfully.
    Subscribers: IngestionWorker (to trigger pipeline for new jobs).
    """
    connector: str
    run_id: str
    jobs_found: int
    jobs_new: int
    jobs_updated: int
    duration_ms: int


class ConnectorRunFailed(HeliosEvent):
    """
    Fired when a connector run fails or times out.
    Subscribers: MonitoringWorker, AlertWorker.
    """
    connector: str
    run_id: str
    error: str
    traceback: Optional[str] = None


class EmbeddingGenerated(HeliosEvent):
    """
    Fired after a vector embedding is stored for an entity.
    Subscribers: RankingWorker (now ready to rank this entity).
    """
    entity_type: str   # "job" | "company" | "user"
    entity_id: str
    model: str
    embedding_id: str


# ── Notification ──────────────────────────────────────────────────────────────

class NotificationRequested(HeliosEvent):
    """
    Fired when any worker determines a user should be notified.
    Subscribers: NotificationWorker → email, push, in-app.
    """
    user_id: str
    type: str    # "new_match" | "deadline_approaching" | "status_change" | "run_failed"
    title: str
    body: str
    action_url: Optional[str] = None
    priority: str = "normal"   # "low" | "normal" | "high"
