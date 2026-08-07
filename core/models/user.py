"""
core/models/user.py

User model. Carries the candidate profile that drives all AI engines.
The profile field maps to the data populated by /setup in the existing
ai-job-search engine.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserSettings(BaseModel):
    """Notification and search preferences."""

    email_notifications: bool = True
    new_match_threshold: float = 0.7        # min fit_score to notify
    max_daily_notifications: int = 10
    preferred_remote: Optional[str] = None   # on_site | remote | hybrid
    preferred_employment: Optional[str] = None
    timezone: str = "Europe/Copenhagen"


class User(BaseModel):
    """
    Helios user / candidate profile.

    The profile dict is the structured representation of CLAUDE.md —
    it carries education, experience, skills, behavioral profile, and
    career goals. AI engines read this to personalize output.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = Field(default=1)
    email: str
    name: Optional[str] = None

    # ── Candidate profile (from /setup) ──────────────────────────────────────
    profile: Optional[dict] = None          # structured candidate profile
    skills: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    target_locations: list[str] = Field(default_factory=list)

    # ── Preferences ───────────────────────────────────────────────────────────
    settings: UserSettings = Field(default_factory=UserSettings)

    # ── Intelligence ──────────────────────────────────────────────────────────
    embedding_id: Optional[str] = None      # FK to user_embeddings, used for matching

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
