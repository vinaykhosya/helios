"""
backend/src/services/job_service.py

JobService implements business logic for Job records.
Interacts with the database purely via JobRepository and CompanyRepository interfaces.
"""
from __future__ import annotations

from typing import Optional
from core.models.job import Job
from core.models.company import Company
from core.interfaces.repository import JobRepository, CompanyRepository


class JobService:
    """Service class for managing Job operations."""

    def __init__(self, job_repo: JobRepository, company_repo: CompanyRepository):
        self._job_repo = job_repo
        self._company_repo = company_repo

    async def create_job(self, job: Job) -> Job:
        """
        Store a new job. Resolves company_name to company_id if possible.
        If company does not exist, a new profile is created.
        """
        # Resolve company
        norm_name = job.company.lower().strip()
        company = await self._company_repo.get_by_normalized_name(norm_name)
        if not company:
            # Create a placeholder company
            company = Company(name=job.company)
            company = await self._company_repo.create(company)

        # Associate job with resolved company
        job_updated = job.model_copy(update={"company_id": company.id})
        return await self._job_repo.create(job_updated)

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Retrieve a job by its UUID."""
        return await self._job_repo.get_by_id(job_id)

    async def get_by_source_id(self, source: str, source_id: str) -> Optional[Job]:
        """Retrieve a job by source and source_id (useful for pipeline deduplication)."""
        return await self._job_repo.get_by_source_id(source, source_id)

    async def update_job(self, job: Job) -> Job:
        """Update an existing job record."""
        return await self._job_repo.update(job)

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> list[Job]:
        """Retrieve a list of jobs ordered by post date descending."""
        return await self._job_repo.list_jobs(limit=limit, offset=offset)
