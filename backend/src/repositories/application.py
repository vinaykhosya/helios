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

    async def create(self, application: Application) -> Application:
        orm = ApplicationMapper.to_orm(application)
        self._session.add(orm)
        await self._session.flush()
        return ApplicationMapper.to_domain(orm)

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
