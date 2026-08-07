"""
backend/src/api/jobs.py

FastAPI route handlers for Job operations.
Exposes CRUD endpoints resolved via DIContainer.
"""
from __future__ import annotations

from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.job import Job
from core.interfaces.repository import JobRepository, CompanyRepository
from backend.src.core.di import DIContainer
from backend.src.services.job_service import JobService

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for database session lifecycle management."""
    async with DIContainer.session() as session:
        yield session


def get_job_service(session: AsyncSession = Depends(get_db_session)) -> JobService:
    """FastAPI Dependency for resolving JobService with injected repository protocols."""
    job_repo = DIContainer.resolve_repository(JobRepository, session)
    company_repo = DIContainer.resolve_repository(CompanyRepository, session)
    return JobService(job_repo, company_repo)


@router.post("", response_model=Job, status_code=status.HTTP_201_CREATED)
async def create_job(job: Job, service: JobService = Depends(get_job_service)) -> Job:
    """Create a new job posting. Links to an existing company or creates a placeholder."""
    return await service.create_job(job)


@router.get("", response_model=list[Job])
async def list_jobs(
    limit: int = 50,
    offset: int = 0,
    service: JobService = Depends(get_job_service),
) -> list[Job]:
    """Retrieve a list of job postings ordered by post date descending."""
    return await service.list_jobs(limit=limit, offset=offset)


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str, service: JobService = Depends(get_job_service)) -> Job:
    """Retrieve a single job posting by its UUID."""
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job not found: {job_id}",
        )
    return job
