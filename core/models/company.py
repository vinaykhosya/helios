"""
core/models/company.py

Company model. Populated by CompanyResolverStage during ingestion.
Enriched progressively as more jobs reference the same company.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CompanySize(str, Enum):
    SEED = "1-10"
    STARTUP = "11-50"
    GROWTH = "51-200"
    MID = "201-500"
    LARGE = "501-1000"
    ENTERPRISE = "1001+"


class Company(BaseModel):
    """
    Company profile.

    Created or updated by CompanyResolverStage when a new job is ingested.
    Enriched asynchronously with external data (LinkedIn, Clearbit, etc.)
    in Phase 3+.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = Field(default=1)
    name: str
    name_normalized: Optional[str] = None   # lowercase, stripped of legal suffixes

    # ── Web presence ──────────────────────────────────────────────────────────
    website: Optional[str] = None
    linkedin_url: Optional[str] = None
    glassdoor_url: Optional[str] = None

    # ── Classification ────────────────────────────────────────────────────────
    industry: Optional[str] = None
    size: Optional[CompanySize] = None
    headquarters: Optional[str] = None
    founded_year: Optional[int] = None

    # ── Content ───────────────────────────────────────────────────────────────
    description: Optional[str] = None
    logo_url: Optional[str] = None

    # ── Intelligence ──────────────────────────────────────────────────────────
    tech_stack: list[str] = Field(default_factory=list)
    salary_benchmark: Optional[dict] = None   # from salary_lookup integration
    embedding_id: Optional[str] = None        # FK to company_embeddings

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"use_enum_values": True}
