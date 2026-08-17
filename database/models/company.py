"""
database/models/company.py

SQLAlchemy ORM models for Companies.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, DateTime, ARRAY, ForeignKey, Integer
from database.models.base import Base, Vector


class CompanyORM(Base):
    """ORM representation of the companies table."""

    __tablename__ = "companies"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    name_normalized: Mapped[Optional[str]] = mapped_column(String, unique=True, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    size: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    glassdoor_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    headquarters: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    founded_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    tech_stack: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    jobs: Mapped[list[JobORM]] = relationship("JobORM", back_populates="company")
    embeddings: Mapped[list[CompanyEmbeddingORM]] = relationship(
        "CompanyEmbeddingORM", back_populates="company", cascade="all, delete-orphan"
    )


class CompanyEmbeddingORM(Base):
    """ORM representation of the company_embeddings table."""

    __tablename__ = "company_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    company_id: Mapped[str] = mapped_column(String, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    company: Mapped[CompanyORM] = relationship("CompanyORM", back_populates="embeddings")
