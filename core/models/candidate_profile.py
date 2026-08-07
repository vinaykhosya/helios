"""
core/models/candidate_profile.py

CandidateProfile — Pydantic domain model for structured candidate data,
hard eligibility constraints, and ranking preferences.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class CandidateProfile(BaseModel):
    """
    Single source of truth for user profile, hard rules, and soft ranking criteria.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    # Candidate Identity & Basics
    name: str = Field(..., description="Full legal name of candidate")
    email: str = Field(..., description="Primary contact email")
    phone: Optional[str] = Field(None, description="Contact phone number")
    location: str = Field(..., description="Current primary location (e.g. 'India')")
    linkedin_url: Optional[str] = Field(None, description="LinkedIn profile URL")
    github_url: Optional[str] = Field(None, description="GitHub profile URL")
    portfolio_url: Optional[str] = Field(None, description="Personal website/portfolio URL")

    # Status & Authorization
    willing_to_relocate: bool = Field(True, description="Willing to relocate")
    requires_sponsorship: bool = Field(False, description="Requires visa sponsorship")
    graduation_year: int = Field(..., description="Year of graduation")
    years_of_experience: float = Field(0.0, description="Total years of professional experience")

    # Hard Constraints (Eligibility Gate)
    min_salary: Optional[float] = Field(None, description="Minimum acceptable annual salary")
    max_experience_years: float = Field(3.0, description="Maximum experience required by job")
    required_tech_stack: list[str] = Field(default_factory=list, description="Must match at least one")
    excluded_keywords: list[str] = Field(default_factory=list, description="Exclude job if title or description contains any")
    target_locations: list[str] = Field(default_factory=list, description="Target location matches")
    excluded_companies: list[str] = Field(default_factory=list, description="Companies to never apply to")
    job_types: list[str] = Field(default_factory=lambda: ["full_time"], description="Accepted employment types")

    # Experience & Resume Bullets (Profile Intelligence)
    experience_bullets: list[str] = Field(default_factory=list, description="Master list of candidate bullet points")
    education_summary: str = Field("", description="Summary of degree and university")

    # Soft Preferences (Ranking Agent)
    preferred_company_sizes: list[str] = Field(default_factory=list)
    preferred_industries: list[str] = Field(default_factory=list)
    ideal_role_keywords: list[str] = Field(default_factory=list)
