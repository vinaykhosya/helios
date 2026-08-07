"""
backend/src/mappers/application_mapper.py

Maps between Application Pydantic Domain Model and ApplicationORM database model.
"""
from __future__ import annotations

from core.models.application import Application, ApplicationStatus
from database.models.application import ApplicationORM


class ApplicationMapper:
    """Translation layer between Application domain and database models."""

    @staticmethod
    def to_domain(orm: ApplicationORM) -> Application:
        """Map ApplicationORM instance to Application domain model."""
        return Application(
            id=orm.id,
            schema_version=1,
            user_id=orm.user_id,
            job_id=orm.job_id,
            status=ApplicationStatus(orm.status),
            applied_at=orm.applied_at,
            resume_id=orm.resume_id,
            cover_letter_id=orm.cover_letter_id,
            fit_rating=float(orm.fit_rating) if orm.fit_rating is not None else None,
            notes=orm.notes,
            contact_person=orm.contact_person,
            source_channel=orm.source_channel,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    @staticmethod
    def to_orm(domain: Application) -> ApplicationORM:
        """Map Application domain model to ApplicationORM instance."""
        return ApplicationORM(
            id=domain.id,
            user_id=domain.user_id,
            job_id=domain.job_id,
            status=domain.status,
            applied_at=domain.applied_at,
            resume_id=domain.resume_id,
            cover_letter_id=domain.cover_letter_id,
            fit_rating=domain.fit_rating,
            notes=domain.notes,
            contact_person=domain.contact_person,
            source_channel=domain.source_channel,
            created_at=domain.created_at,
            updated_at=domain.updated_at,
        )
