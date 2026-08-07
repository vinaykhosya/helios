"""
database/models/user.py

SQLAlchemy ORM models for Users.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, JSON, DateTime, ARRAY, ForeignKey
from database.models.base import Base

# Conditionally import vector if pgvector is available, otherwise mock it
try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    from sqlalchemy import ARRAY as Vector  # fallback for typing


class UserORM(Base):
    """ORM representation of the users table."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    profile: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    target_roles: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    target_locations: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    skills: Mapped[Optional[list[str]]] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications: Mapped[list[ApplicationORM]] = relationship(
        "ApplicationORM", back_populates="user", cascade="all, delete-orphan"
    )
    resumes: Mapped[list[ResumeORM]] = relationship(
        "ResumeORM", back_populates="user", cascade="all, delete-orphan"
    )
    cover_letters: Mapped[list[CoverLetterORM]] = relationship(
        "CoverLetterORM", back_populates="user", cascade="all, delete-orphan"
    )
    saved_jobs: Mapped[list[SavedJobORM]] = relationship(
        "SavedJobORM", back_populates="user", cascade="all, delete-orphan"
    )
    skill_analytics: Mapped[list[SkillAnalyticsORM]] = relationship(
        "SkillAnalyticsORM", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[list[NotificationORM]] = relationship(
        "NotificationORM", back_populates="user", cascade="all, delete-orphan"
    )
    embeddings: Mapped[list[UserEmbeddingORM]] = relationship(
        "UserEmbeddingORM", back_populates="user", cascade="all, delete-orphan"
    )


class UserEmbeddingORM(Base):
    """ORM representation of the user_embeddings table."""

    __tablename__ = "user_embeddings"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    user: Mapped[UserORM] = relationship("UserORM", back_populates="embeddings")
