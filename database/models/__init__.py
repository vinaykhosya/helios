"""
database/models/__init__.py

Exposes all SQLAlchemy ORM models and the Declarative Base.
Imports are ordered carefully to resolve circular forward references.
"""
from database.models.base import Base

# Import ORMs to register in Metadata
from database.models.user import UserORM, UserEmbeddingORM
from database.models.company import CompanyORM, CompanyEmbeddingORM
from database.models.job import JobORM, JobEmbeddingORM
from database.models.application import ApplicationORM, ResumeORM, CoverLetterORM, InterviewSessionORM
from database.models.analytics import SavedJobORM, SkillAnalyticsORM
from database.models.system import (
    NotificationORM,
    ConnectorHealthORM,
    ConnectorRunORM,
    ConnectorErrorORM,
    AuditLogORM,
)
from database.models.human_queue import HumanQueueORM  # noqa
from database.models.integrations import GoogleSheetsConfigORM  # noqa

__all__ = [
    "Base",
    # User
    "UserORM",
    "UserEmbeddingORM",
    # Company
    "CompanyORM",
    "CompanyEmbeddingORM",
    # Job
    "JobORM",
    "JobEmbeddingORM",
    # Application
    "ApplicationORM",
    "ResumeORM",
    "CoverLetterORM",
    "InterviewSessionORM",
    # Analytics
    "SavedJobORM",
    "SkillAnalyticsORM",
    # System
    "NotificationORM",
    "ConnectorHealthORM",
    "ConnectorRunORM",
    "ConnectorErrorORM",
    "AuditLogORM",
    # Human Queue
    "HumanQueueORM",
]
