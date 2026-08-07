"""
database/models/application.py

SQLAlchemy ORM models for Applications, Resumes, Cover Letters, and Interview Sessions.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, DateTime, ForeignKey, Numeric, Integer, Boolean
from database.models.base import Base


class ApplicationORM(Base):
    """ORM representation of the applications table."""

    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="saved")
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resume_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("resumes.id", use_alter=True, name="fk_applications_resume"), nullable=True)
    cover_letter_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("cover_letters.id", use_alter=True, name="fk_applications_cover_letter"), nullable=True)
    fit_rating: Mapped[Optional[float]] = mapped_column(Numeric(4, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source_channel: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped[UserORM] = relationship("UserORM", back_populates="applications")
    job: Mapped[Optional[JobORM]] = relationship("JobORM", back_populates="applications")
    interview_sessions: Mapped[list[InterviewSessionORM]] = relationship(
        "InterviewSessionORM", back_populates="application", cascade="all, delete-orphan"
    )

    # Explicit relationships for resume & cover letter to avoid circular issues
    resume: Mapped[Optional[ResumeORM]] = relationship("ResumeORM", foreign_keys=[resume_id])
    cover_letter: Mapped[Optional[CoverLetterORM]] = relationship("CoverLetterORM", foreign_keys=[cover_letter_id])


class ResumeORM(Base):
    """ORM representation of the resumes table."""

    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id"), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    latex_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_master: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user: Mapped[UserORM] = relationship("UserORM", back_populates="resumes")
    job: Mapped[Optional[JobORM]] = relationship("JobORM", back_populates="resumes")


class CoverLetterORM(Base):
    """ORM representation of the cover_letters table."""

    __tablename__ = "cover_letters"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("jobs.id"), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    latex_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    language: Mapped[str] = mapped_column(String, default="en")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user: Mapped[UserORM] = relationship("UserORM", back_populates="cover_letters")
    job: Mapped[Optional[JobORM]] = relationship("JobORM", back_populates="cover_letters")


class InterviewSessionORM(Base):
    """ORM representation of the interview_sessions table."""

    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("applications.id"), nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    questions: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    answers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    talking_points: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    application: Mapped[Optional[ApplicationORM]] = relationship("ApplicationORM", back_populates="interview_sessions")
