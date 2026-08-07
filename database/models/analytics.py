"""
database/models/analytics.py

SQLAlchemy ORM models for Saved Jobs and Skill Analytics.
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, DateTime, Date, ForeignKey
from database.models.base import Base


class SavedJobORM(Base):
    """ORM representation of the saved_jobs table."""

    __tablename__ = "saved_jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    fit_score: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user: Mapped[UserORM] = relationship("UserORM", back_populates="saved_jobs")
    job: Mapped[JobORM] = relationship("JobORM", back_populates="saved_jobs")


class SkillAnalyticsORM(Base):
    """ORM representation of the skill_analytics table."""

    __tablename__ = "skill_analytics"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill: Mapped[str] = mapped_column(String, nullable=False)
    gap_score: Mapped[Optional[float]] = mapped_column(Numeric(5, 2), nullable=True)
    gap_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_mode: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    report_date: Mapped[date] = mapped_column(Date, default=date.today)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user: Mapped[UserORM] = relationship("UserORM", back_populates="skill_analytics")
