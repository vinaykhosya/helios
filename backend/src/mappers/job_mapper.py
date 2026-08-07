"""
backend/src/mappers/job_mapper.py

Maps between Job Pydantic Domain Model and JobORM database model.
"""
from __future__ import annotations

from datetime import datetime
from core.models.job import Job, JobSource, RemotePolicy, EmploymentType, Salary, SalaryConfidence
from database.models.job import JobORM


class JobMapper:
    """Translation layer between Job domain and database models."""

    @staticmethod
    def _parse_list(val: any) -> list[str]:
        if isinstance(val, str):
            import json
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return val or []

    @staticmethod
    def to_domain(orm: JobORM) -> Job:
        """Map JobORM instance to Job domain model."""
        salary = None
        if orm.salary_min is not None or orm.salary_max is not None or orm.salary_raw:
            salary = Salary(
                min=orm.salary_min,
                max=orm.salary_max,
                currency=orm.salary_currency,
                raw_text=orm.salary_raw,
                confidence=SalaryConfidence(orm.salary_confidence),
            )

        languages = JobMapper._parse_list(orm.languages_required)
        benefits = JobMapper._parse_list(orm.benefits)
        skills = JobMapper._parse_list(orm.skills)

        # Deserialize raw_data if string (sqlite JSON storage)
        raw_data = orm.raw_data or {}
        if isinstance(raw_data, str):
            import json
            try:
                raw_data = json.loads(raw_data)
            except Exception:
                raw_data = {}

        return Job(
            id=orm.id,
            schema_version=1,
            source=JobSource(orm.source),
            source_id=orm.source_id,
            source_url=orm.source_url,
            title=orm.title,
            description=orm.description,
            company=orm.company_name,
            company_url=None,
            company_id=orm.company_id,
            location=orm.location,
            city=orm.city,
            country=orm.country,
            remote=RemotePolicy(orm.remote),
            relocation_supported=orm.relocation_supported,
            visa_sponsorship=orm.visa_sponsorship,
            employment_type=EmploymentType(orm.employment_type),
            seniority=orm.seniority,
            experience_years=orm.experience_years,
            education_required=orm.education_required,
            security_clearance=orm.security_clearance,
            languages_required=languages,
            salary=salary,
            benefits=benefits,
            skills=skills,
            industry=orm.industry,
            posted_date=orm.posted_date,
            deadline=orm.deadline,
            apply_url=orm.apply_url,
            is_active=orm.is_active,
            idempotency_key=orm.idempotency_key,
            raw_data=raw_data,
            fetched_at=orm.fetched_at,
        )

    @staticmethod
    def to_orm(domain: Job) -> JobORM:
        """Map Job domain model to JobORM instance."""
        salary_min = domain.salary.min if domain.salary else None
        salary_max = domain.salary.max if domain.salary else None
        salary_currency = domain.salary.currency if domain.salary else "DKK"
        salary_raw = domain.salary.raw_text if domain.salary else None
        salary_confidence = domain.salary.confidence if domain.salary else "unknown"

        return JobORM(
            id=domain.id,
            source=domain.source,
            source_id=domain.source_id,
            source_url=domain.source_url,
            title=domain.title,
            description=domain.description,
            company_id=domain.company_id,
            company_name=domain.company,
            location=domain.location,
            city=domain.city,
            country=domain.country or "Denmark",
            remote=domain.remote,
            relocation_supported=domain.relocation_supported,
            visa_sponsorship=domain.visa_sponsorship,
            employment_type=domain.employment_type,
            seniority=domain.seniority,
            experience_years=domain.experience_years,
            education_required=domain.education_required,
            security_clearance=domain.security_clearance,
            languages_required=domain.languages_required,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            salary_raw=salary_raw,
            salary_confidence=salary_confidence,
            benefits=domain.benefits,
            skills=domain.skills,
            industry=domain.industry,
            posted_date=domain.posted_date,
            deadline=domain.deadline,
            apply_url=domain.apply_url,
            is_active=domain.is_active,
            idempotency_key=domain.idempotency_key,
            raw_data=domain.raw_data,
            fetched_at=domain.fetched_at,
            created_at=datetime.utcnow(),
        )
