"""
core/interfaces/repository.py

Repository Protocols.
Services import these protocols rather than concrete repository classes.
This enables clean Dependency Injection and mock repository usage in unit tests.
"""
from __future__ import annotations

from typing import Optional, Protocol
from core.models.job import Job
from core.models.company import Company
from core.models.application import Application
from core.models.user import User


class JobRepository(Protocol):
    """Protocol for Job data access operations."""

    async def create(self, job: Job) -> Job:
        """Store a new job record."""
        ...

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        """Retrieve a job by its UUID."""
        ...

    async def get_by_source_id(self, source: str, source_id: str) -> Optional[Job]:
        """Retrieve a job by its source and source-native ID."""
        ...

    async def update(self, job: Job) -> Job:
        """Update an existing job record."""
        ...

    async def delete(self, job_id: str) -> bool:
        """Delete a job record by ID. Returns True if deleted."""
        ...

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> list[Job]:
        """Retrieve a paginated list of jobs."""
        ...


class CompanyRepository(Protocol):
    """Protocol for Company data access operations."""

    async def create(self, company: Company) -> Company:
        ...

    async def get_by_id(self, company_id: str) -> Optional[Company]:
        ...

    async def get_by_normalized_name(self, name_normalized: str) -> Optional[Company]:
        ...

    async def update(self, company: Company) -> Company:
        ...

    async def list_companies(self, limit: int = 50, offset: int = 0) -> list[Company]:
        ...


class ApplicationRepository(Protocol):
    """Protocol for Application data access operations."""

    async def create(self, application: Application) -> Application:
        ...

    async def get_by_id(self, application_id: str) -> Optional[Application]:
        ...

    async def get_by_user_and_job(self, user_id: str, job_id: str) -> Optional[Application]:
        ...

    async def update(self, application: Application) -> Application:
        ...

    async def list_by_user(self, user_id: str) -> list[Application]:
        ...


class UserRepository(Protocol):
    """Protocol for User data access operations."""

    async def create(self, user: User) -> User:
        ...

    async def get_by_id(self, user_id: str) -> Optional[User]:
        ...

    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    async def update(self, user: User) -> User:
        ...


class EmbeddingRepository(Protocol):
    """Protocol for vector embedding persistence and retrieval."""

    async def store(self, entity_id: str, embedding_id: str, vector: list[float], model: str) -> None:
        """Store embedding vector for an entity (job)."""
        ...

    async def get_by_id(self, embedding_id: str) -> Optional[dict]:
        """Retrieve stored embedding record by embedding UUID."""
        ...

    async def get_by_job_id(self, job_id: str) -> Optional[dict]:
        """Retrieve stored embedding record by job UUID."""
        ...
