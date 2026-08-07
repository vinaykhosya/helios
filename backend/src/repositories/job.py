"""
backend/src/repositories/job.py

SQLAlchemyJobRepository concrete implementation of core.interfaces.JobRepository.
Converts ORM model (JobORM) instances to/from Domain Pydantic models (Job).
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from core.models.job import Job
from core.interfaces.repository import JobRepository
from database.models.job import JobORM
from backend.src.mappers.job_mapper import JobMapper


class SQLAlchemyJobRepository(JobRepository):
    """SQLAlchemy implementation of the JobRepository protocol."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, job: Job) -> Job:
        orm = JobMapper.to_orm(job)
        self._session.add(orm)
        await self._session.flush()
        return JobMapper.to_domain(orm)

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        stmt = select(JobORM).where(JobORM.id == job_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return JobMapper.to_domain(orm) if orm else None

    async def get_by_source_id(self, source: str, source_id: str) -> Optional[Job]:
        stmt = select(JobORM).where(JobORM.source == source, JobORM.source_id == source_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return JobMapper.to_domain(orm) if orm else None

    async def update(self, job: Job) -> Job:
        stmt = select(JobORM).where(JobORM.id == job.id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if not orm:
            from core.exceptions import JobNotFoundError
            raise JobNotFoundError(f"Job not found for update: {job.id}")

        # Update columns
        orm.title = job.title
        orm.description = job.description
        orm.company_id = job.company_id
        orm.company_name = job.company
        orm.location = job.location
        orm.city = job.city
        orm.country = job.country or "Denmark"
        orm.remote = job.remote
        orm.relocation_supported = job.relocation_supported
        orm.visa_sponsorship = job.visa_sponsorship
        orm.employment_type = job.employment_type
        orm.seniority = job.seniority
        orm.experience_years = job.experience_years
        orm.education_required = job.education_required
        orm.security_clearance = job.security_clearance
        orm.languages_required = job.languages_required

        if job.salary:
            orm.salary_min = job.salary.min
            orm.salary_max = job.salary.max
            orm.salary_currency = job.salary.currency
            orm.salary_raw = job.salary.raw_text
            orm.salary_confidence = job.salary.confidence

        orm.benefits = job.benefits
        orm.skills = job.skills
        orm.industry = job.industry
        orm.posted_date = job.posted_date
        orm.deadline = job.deadline
        orm.apply_url = job.apply_url
        orm.is_active = job.is_active
        orm.raw_data = job.raw_data

        await self._session.flush()
        return JobMapper.to_domain(orm)

    async def delete(self, job_id: str) -> bool:
        stmt = delete(JobORM).where(JobORM.id == job_id)
        res = await self._session.execute(stmt)
        await self._session.flush()
        return bool(res.rowcount > 0)

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> list[Job]:
        stmt = select(JobORM).offset(offset).limit(limit).order_by(JobORM.posted_date.desc())
        res = await self._session.execute(stmt)
        orms = res.scalars().all()
        return [JobMapper.to_domain(o) for o in orms]
