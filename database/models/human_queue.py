"""database/models/human_queue.py -- HumanQueueORM."""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import String, JSON, DateTime, ForeignKey, Numeric, Integer, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from database.models.base import Base


class HumanQueueORM(Base):
    __tablename__ = "human_queue"

    id: Mapped[str]          = mapped_column(String, primary_key=True)
    user_id: Mapped[str]     = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"))
    job_id: Mapped[str]      = mapped_column(String, ForeignKey("jobs.id"))
    application_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("applications.id"), nullable=True
    )

    # Telegram metadata -- NOT part of state machine, updated via set_telegram_pending_id()
    telegram_pending_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    telegram_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # State machine
    decision: Mapped[str] = mapped_column(String, default="pending")

    # Scores
    fit_score: Mapped[Optional[float]]        = mapped_column(Numeric(4, 2), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    friction_score: Mapped[int]               = mapped_column(Integer, default=0)
    routing_reason: Mapped[Optional[str]]     = mapped_column(Text, nullable=True)

    # Application package
    resume_path: Mapped[Optional[str]]     = mapped_column(String, nullable=True)
    application_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    matching_skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    missing_skills: Mapped[Optional[list]]  = mapped_column(JSON, nullable=True)

    # Google Sheets (push-only V1)
    sheets_row_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    sheets_last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_sheets_snapshot: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Timing
    created_at: Mapped[datetime]           = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
