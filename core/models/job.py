"""
core/models/job.py

Universal Job model. Every connector must produce a Job.
Every AI engine, ranking stage, and service consumes a Job.
This is the central data contract of the Helios platform.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RemotePolicy(str, Enum):
    ON_SITE = "on_site"
    REMOTE = "remote"
    HYBRID = "hybrid"


class JobSource(str, Enum):
    """All supported job portal connectors."""
    JOBBANK = "jobbank"
    JOBDANMARK = "jobdanmark"
    JOBINDEX = "jobindex"
    JOBNET = "jobnet"
    LINKEDIN = "linkedin"
    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    WELLFOUND = "wellfound"
    REMOTEOK = "remoteok"
    NAUKRI = "naukri"
    MANUAL = "manual"  # user-entered jobs


class EmploymentType(str, Enum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    FREELANCE = "freelance"
    INTERNSHIP = "internship"
    VOLUNTEER = "volunteer"


class SalaryConfidence(str, Enum):
    EXPLICIT = "explicit"    # stated directly in the posting
    ESTIMATED = "estimated"  # inferred by AI from description
    UNKNOWN = "unknown"      # no salary information available


class Salary(BaseModel):
    """Compensation details for a job posting."""

    min: Optional[int] = None
    max: Optional[int] = None
    currency: str = "DKK"
    period: str = "annual"       # annual | monthly | hourly
    raw_text: Optional[str] = None
    confidence: SalaryConfidence = SalaryConfidence.UNKNOWN

    model_config = {"use_enum_values": True}


class Job(BaseModel):
    """
    Universal Job model.

    Connectors produce this. Services store this. AI engines consume this.
    Every field that a connector cannot populate defaults to None or an
    empty list — never raises on partial data.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    schema_version: int = Field(default=1)
    source: JobSource
    source_id: str        # portal's own identifier
    source_url: str       # canonical URL on the portal

    # ── Content ───────────────────────────────────────────────────────────────
    title: str
    description: Optional[str] = None
    company: str
    company_url: Optional[str] = None
    company_id: Optional[str] = None    # resolved by CompanyResolverStage

    # ── Location ──────────────────────────────────────────────────────────────
    location: Optional[str] = None      # raw location string from portal
    city: Optional[str] = None
    country: Optional[str] = None
    remote: RemotePolicy = RemotePolicy.ON_SITE
    relocation_supported: bool = False
    visa_sponsorship: bool = False

    # ── Role classification ───────────────────────────────────────────────────
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    seniority: Optional[str] = None     # junior | mid | senior | lead | principal
    experience_years: Optional[int] = None   # minimum years required
    education_required: Optional[str] = None
    security_clearance: bool = False
    languages_required: list[str] = Field(default_factory=list)

    # ── Compensation ──────────────────────────────────────────────────────────
    salary: Optional[Salary] = None
    benefits: list[str] = Field(default_factory=list)

    # ── Taxonomy ──────────────────────────────────────────────────────────────
    skills: list[str] = Field(default_factory=list)
    industry: Optional[str] = None

    # ── Timing ────────────────────────────────────────────────────────────────
    posted_date: Optional[datetime] = None
    deadline: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    # ── Application ───────────────────────────────────────────────────────────
    apply_url: Optional[str] = None

    # ── Intelligence (populated by pipeline stages) ───────────────────────────
    fit_score: Optional[float] = None        # 0.0–1.0, set by RankerStage
    embedding_id: Optional[str] = None       # FK to job_embeddings, set by EmbeddingGeneratorStage
    is_active: bool = True
    idempotency_key: Optional[str] = None     # SHA256(source + source_id + updated_at)

    # ── Raw portal payload (preserved for debugging and re-parsing) ───────────
    raw_data: dict = Field(default_factory=dict)

    model_config = {"use_enum_values": True}
