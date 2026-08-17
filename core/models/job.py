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
    ASHBY = "ashby"
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


class FreshnessStatus(str, Enum):
    """Orthogonal job age classification."""
    FRESH = "FRESH"            # age <= 7 days (Configurable)
    AGING = "AGING"            # 8–14 days
    STALE = "STALE"            # 15–30 days
    VERY_STALE = "VERY_STALE"  # > 30 days
    UNKNOWN = "UNKNOWN"        # reliable date unavailable (fail-closed for ready-to-apply)


class FreshnessConfidence(str, Enum):
    """Provenance tracking for job age calculation."""
    CONFIRMED_POSTED = "CONFIRMED_POSTED"      # Exact publication timestamp from ATS
    CONFIRMED_REPOSTED = "CONFIRMED_REPOSTED"  # Verified renewed publication timestamp
    INFERRED = "INFERRED"                      # Parsed relative string ("2 days ago")
    UNKNOWN = "UNKNOWN"                        # No reliable date available


class RoleFamily(str, Enum):
    """Taxonomic job family classification."""
    MACHINE_LEARNING_AI = "MACHINE_LEARNING_AI"      # Core ML/AI, Deep Learning, NLP, CV, LLM, MLOps
    BACKEND_SYSTEMS = "BACKEND_SYSTEMS"              # Backend, Distributed Systems, Python/Go/C++ Systems
    DATA_ENGINEERING = "DATA_ENGINEERING"            # Data Platform, ETL, Analytics Engineering
    GENERIC_SOFTWARE = "GENERIC_SOFTWARE"            # General Software Engineer, Full Stack, Frontend
    SOLUTIONS_PRE_SALES = "SOLUTIONS_PRE_SALES"      # Solutions Architect, Partner Engineer, Pre-Sales
    RECRUITING_HR = "RECRUITING_HR"                  # Recruiter, Talent Acquisition, Human Resources
    CUSTOMER_SUPPORT = "CUSTOMER_SUPPORT"            # Customer Support, Help Desk, Service Rep
    SALES_MARKETING = "SALES_MARKETING"              # Account Exec, BDM, Marketing, Growth
    MANAGEMENT_EXECUTIVE = "MANAGEMENT_EXECUTIVE"    # Engineering Manager, Director, VP, CTO
    OTHER_NON_TECH = "OTHER_NON_TECH"                # Legal, Accounting, Admin, Operations


class RoleRelevance(str, Enum):
    """Candidate profile alignment level (Orthogonal to Match Score)."""
    TARGET = "TARGET"        # Core match (e.g. ML/AI for ML profile)
    ADJACENT = "ADJACENT"    # Related technical role; requires JD ML evidence for Ready-to-Apply
    IRRELEVANT = "IRRELEVANT"# Strictly non-target / non-engineering; fail-closed from Ready-to-Apply
    UNKNOWN = "UNKNOWN"      # Insufficient evidence; fail-closed for Ready-to-Apply


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

    # ── Timing & Freshness Provenance (Auditable Job OS) ──────────────────────
    posted_date: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    last_updated_at: Optional[datetime] = None
    is_reposted: bool = False
    reposted_at: Optional[datetime] = None
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    freshness_reference_at: Optional[datetime] = None
    age_days: Optional[int] = None
    freshness_status: FreshnessStatus = FreshnessStatus.UNKNOWN
    freshness_confidence: FreshnessConfidence = FreshnessConfidence.UNKNOWN
    freshness_source: Optional[str] = None
    date_anomaly: Optional[str] = None  # None | "FUTURE_TIMESTAMP" | "MALFORMED_INPUT"
    deadline: Optional[datetime] = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)

    # ── Application & Availability ────────────────────────────────────────────
    apply_url: Optional[str] = None
    is_closed: bool = False
    availability: str = "OPEN"  # OPEN | CLOSED | UNKNOWN

    # ── Role Relevance & Taxonomic Intelligence (Orthogonal to Match Score) ──
    role_family: Optional[RoleFamily] = None
    role_relevance: RoleRelevance = RoleRelevance.UNKNOWN
    role_relevance_confidence: float = 0.0
    role_relevance_reasons: list[str] = Field(default_factory=list)
    evidence_keywords: list[str] = Field(default_factory=list)
    adjacent_ml_evidence_score: float = 0.0

    # ── Intelligence & Eligibility (populated by pipeline stages) ───────────
    fit_score: Optional[float] = None        # 0.0–1.0, set by RankerStage (unmodified by age/relevance)
    embedding_id: Optional[str] = None       # FK to job_embeddings, set by EmbeddingGeneratorStage
    eligibility_status: str = "ELIGIBLE"     # ELIGIBLE | SENIORITY_MISMATCH | ROLE_MISMATCH | LOCATION_MISMATCH
    eligibility_reasons: list[str] = Field(default_factory=list)
    duplicate_group_id: Optional[str] = None
    source_count: int = 1
    dimension_breakdown: dict[str, float] = Field(default_factory=dict)
    friction_level: str = "LOW"
    application_status: str = "NOT_APPLIED"  # NOT_APPLIED | APPLIED | SKIPPED
    is_active: bool = True
    idempotency_key: Optional[str] = None     # SHA256(source + source_id + updated_at)

    # ── Raw portal payload (preserved for debugging and re-parsing) ───────────
    raw_data: dict = Field(default_factory=dict)

    model_config = {"use_enum_values": True}
