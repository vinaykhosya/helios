"""
database/models/job.py

SQLAlchemy ORM models for Jobs and Job Embeddings.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, DateTime, ARRAY, ForeignKey, Integer, Boolean, Float
from database.models.base import Base, Vector


class JobORM(Base):
    """ORM representation of the jobs table."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[str] = mapped_column(String, nullable=False)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    company_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("companies.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String, nullable=False)

    location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    country: Mapped[str] = mapped_column(String, default="Denmark")
    remote: Mapped[str] = mapped_column(String, default="on_site")
    relocation_supported: Mapped[bool] = mapped_column(Boolean, default=False)
    visa_sponsorship: Mapped[bool] = mapped_column(Boolean, default=False)

    employment_type: Mapped[str] = mapped_column(String, default="full_time")
    seniority: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    education_required: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    security_clearance: Mapped[bool] = mapped_column(Boolean, default=False)
    languages_required: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String, default="DKK")
    salary_raw: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    salary_confidence: Mapped[str] = mapped_column(String, default="unknown")
    benefits: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)

    skills: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    posted_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_reposted: Mapped[bool] = mapped_column(Boolean, default=False)
    reposted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    freshness_reference_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    age_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    freshness_status: Mapped[str] = mapped_column(String, default="UNKNOWN")
    freshness_confidence: Mapped[str] = mapped_column(String, default="UNKNOWN")
    freshness_source: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    date_anomaly: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role_family: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role_relevance: Mapped[str] = mapped_column(String, default="UNKNOWN")
    role_relevance_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    adjacent_ml_evidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    apply_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)
    availability: Mapped[str] = mapped_column(String, default="OPEN")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)

    raw_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    company: Mapped[Optional[CompanyORM]] = relationship("CompanyORM", back_populates="jobs")
    applications: Mapped[list[ApplicationORM]] = relationship("ApplicationORM", back_populates="job")
    saved_jobs: Mapped[list[SavedJobORM]] = relationship("SavedJobORM", back_populates="job", cascade="all, delete-orphan")
    resumes: Mapped[list[ResumeORM]] = relationship("ResumeORM", back_populates="job")
    cover_letters: Mapped[list[CoverLetterORM]] = relationship("CoverLetterORM", back_populates="job")
    embeddings: Mapped[list[JobEmbeddingORM]] = relationship(
        "JobEmbeddingORM", back_populates="job", cascade="all, delete-orphan"
    )


class JobEmbeddingORM(Base):
    """ORM representation of the job_embeddings table."""

    __tablename__ = "job_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    job_id: Mapped[str] = mapped_column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    job: Mapped[JobORM] = relationship("JobORM", back_populates="embeddings")
