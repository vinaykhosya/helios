"""
database/models/system.py

SQLAlchemy ORM models for System operations: Notifications, Connector runs, errors, health, and Audit logs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, DateTime, ForeignKey, Integer, Boolean, Numeric
from database.models.base import Base


class NotificationORM(Base):
    """ORM representation of the notifications table."""

    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    body: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user: Mapped[UserORM] = relationship("UserORM", back_populates="notifications")


class ConnectorHealthORM(Base):
    """ORM representation of the connector_health table."""

    __tablename__ = "connector_health"

    connector: Mapped[str] = mapped_column(String, primary_key=True)
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    jobs_seen: Mapped[int] = mapped_column(Integer, default=0)
    jobs_inserted: Mapped[int] = mapped_column(Integer, default=0)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)
    success_rate: Mapped[float] = mapped_column(Numeric, default=100.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class DeadLetterQueueORM(Base):
    """ORM representation of the dead_letter_queue table."""

    __tablename__ = "dead_letter_queue"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    connector: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    exception_type: Mapped[str] = mapped_column(String, nullable=False)
    exception_message: Mapped[str] = mapped_column(String, nullable=False)
    stack_trace: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    last_retry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    correlation_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="NEW")


class ConnectorRunORM(Base):
    """ORM representation of the connector_runs table."""

    __tablename__ = "connector_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    connector: Mapped[str] = mapped_column(String, nullable=False)
    trigger: Mapped[str] = mapped_column(String, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    jobs_found: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    jobs_new: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    jobs_updated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, default="running")
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Relationships
    errors: Mapped[list[ConnectorErrorORM]] = relationship(
        "ConnectorErrorORM", back_populates="run", cascade="all, delete-orphan"
    )


class ConnectorErrorORM(Base):
    """ORM representation of the connector_errors table."""

    __tablename__ = "connector_errors"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    run_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("connector_runs.id"), nullable=True)
    connector: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    traceback: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    run: Mapped[Optional[ConnectorRunORM]] = relationship("ConnectorRunORM", back_populates="errors")


class AuditLogORM(Base):
    """ORM representation of the audit_logs table."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    before: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    after: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
