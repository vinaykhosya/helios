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
