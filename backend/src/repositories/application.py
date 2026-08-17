"""
backend/src/repositories/application.py

SQLAlchemyApplicationRepository concrete implementation of core.interfaces.ApplicationRepository.
Converts ORM model (ApplicationORM) instances to/from Domain Pydantic models (Application).
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models.application import Application
from core.interfaces.repository import ApplicationRepository
from database.models.application import ApplicationORM
from backend.src.mappers.application_mapper import ApplicationMapper
from datetime import datetime


class SQLAlchemyApplicationRepository(ApplicationRepository):
    """SQLAlchemy implementation of the ApplicationRepository protocol."""

    def __init__(self, session: AsyncSession):
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def create(self, application: Application) -> Application:
        orm = ApplicationMapper.to_orm(application)
        self._session.add(orm)
        await self._session.flush()
        return ApplicationMapper.to_domain(orm)

    async def create_within_transaction(self, application: Application) -> Application:
        """Create application inside an active transaction context without explicit commit."""
        return await self.create(application)

    async def get_by_id(self, application_id: str) -> Optional[Application]:
        stmt = select(ApplicationORM).where(ApplicationORM.id == application_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return ApplicationMapper.to_domain(orm) if orm else None

    async def get_by_user_and_job(self, user_id: str, job_id: str) -> Optional[Application]:
        stmt = select(ApplicationORM).where(ApplicationORM.user_id == user_id, ApplicationORM.job_id == job_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return ApplicationMapper.to_domain(orm) if orm else None

    async def update(self, application: Application) -> Application:
        stmt = select(ApplicationORM).where(ApplicationORM.id == application.id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if not orm:
            from core.exceptions import ApplicationNotFoundError
            raise ApplicationNotFoundError(f"Application not found for update: {application.id}")

        orm.status = application.status
        orm.applied_at = application.applied_at
        orm.resume_id = application.resume_id
        orm.cover_letter_id = application.cover_letter_id
        orm.fit_rating = application.fit_rating
        orm.notes = application.notes
        orm.contact_person = application.contact_person
        orm.source_channel = application.source_channel
        orm.updated_at = datetime.utcnow()

        await self._session.flush()
        return ApplicationMapper.to_domain(orm)

    async def list_by_user(self, user_id: str) -> list[Application]:
        stmt = select(ApplicationORM).where(ApplicationORM.user_id == user_id).order_by(ApplicationORM.updated_at.desc())
        res = await self._session.execute(stmt)
        orms = res.scalars().all()
        return [ApplicationMapper.to_domain(o) for o in orms]

    async def list_open_with_company_info(self, user_id: str) -> list[dict]:
        """
        Returns list of open applications formatted for EmailApplicationMatcher.
        Includes company domain, company name, role title, and apply_url.
        """
        from database.models.job import JobORM
        from database.models.company import CompanyORM

        stmt = (
            select(
                ApplicationORM.id,
                ApplicationORM.status,
                JobORM.title.label("job_title"),
                JobORM.apply_url,
                JobORM.source_url,
                CompanyORM.name.label("company_name"),
                CompanyORM.domain.label("company_domain"),
            )
            .outerjoin(JobORM, ApplicationORM.job_id == JobORM.id)
            .outerjoin(CompanyORM, JobORM.company_id == CompanyORM.id)
            .where(
                ApplicationORM.user_id == user_id,
                ApplicationORM.status.in_(["pending_manual", "submitted_manual", "applied", "technical", "phone_screen"]),
            )
        )
        res = await self._session.execute(stmt)
        rows = res.all()
        out = []
        for r in rows:
            company_name = r.company_name or ""
            domain = r.company_domain or ""
            if not domain and company_name:
                domain = f"{company_name.lower().replace(' ', '')}.com"
            out.append({
                "id": r.id,
                "status": r.status,
                "job_title": r.job_title or "",
                "apply_url": r.apply_url or r.source_url or "",
                "company_name": company_name,
                "company_domain": domain,
            })
        return out

    async def update_status(self, application_id: str, new_status: str) -> None:
        """Update only the status and updated_at of an application."""
        stmt = select(ApplicationORM).where(ApplicationORM.id == application_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if orm:
            orm.status = new_status
            orm.updated_at = datetime.utcnow()
            await self._session.flush()
