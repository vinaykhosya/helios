"""
core/models/__init__.py

Re-exports all universal models for convenient importing:
    from core.models import Job, Company, Application, User
"""
from core.models.application import Application, ApplicationStatus
from core.models.candidate_profile import CandidateProfile
from core.models.company import Company, CompanySize
from core.models.job import (
    EmploymentType,
    Job,
    JobSource,
    RemotePolicy,
    Salary,
    SalaryConfidence,
)
from core.models.user import User, UserSettings

__all__ = [
    # Job
    "Job",
    "JobSource",
    "RemotePolicy",
    "EmploymentType",
    "Salary",
    "SalaryConfidence",
    # Company
    "Company",
    "CompanySize",
    # Application
    "Application",
    "ApplicationStatus",
    # User
    "User",
    "UserSettings",
    # Candidate Profile
    "CandidateProfile",
]

