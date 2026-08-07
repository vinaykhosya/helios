"""
backend/src/repositories/company.py

SQLAlchemyCompanyRepository concrete implementation of core.interfaces.CompanyRepository.
Converts ORM model (CompanyORM) instances to/from Domain Pydantic models (Company).
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models.company import Company
from core.interfaces.repository import CompanyRepository
from database.models.company import CompanyORM
from backend.src.mappers.company_mapper import CompanyMapper


class SQLAlchemyCompanyRepository(CompanyRepository):
    """SQLAlchemy implementation of the CompanyRepository protocol."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, company: Company) -> Company:
        orm = CompanyMapper.to_orm(company)
        self._session.add(orm)
        await self._session.flush()
        return CompanyMapper.to_domain(orm)

    async def get_by_id(self, company_id: str) -> Optional[Company]:
        stmt = select(CompanyORM).where(CompanyORM.id == company_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return CompanyMapper.to_domain(orm) if orm else None

    async def get_by_normalized_name(self, name_normalized: str) -> Optional[Company]:
        stmt = select(CompanyORM).where(CompanyORM.name_normalized == name_normalized)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return CompanyMapper.to_domain(orm) if orm else None

    async def update(self, company: Company) -> Company:
        stmt = select(CompanyORM).where(CompanyORM.id == company.id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if not orm:
            from core.exceptions import CompanyNotFoundError
            raise CompanyNotFoundError(f"Company not found for update: {company.id}")

        orm.name = company.name
        orm.name_normalized = company.name.lower().strip()
        orm.website = company.website
        orm.industry = company.industry
        orm.size = company.size
        orm.description = company.description
        orm.logo_url = company.logo_url
        orm.linkedin_url = company.linkedin_url
        orm.glassdoor_url = company.glassdoor_url
        orm.headquarters = company.headquarters
        orm.founded_year = company.founded_year
        orm.salary_data = company.salary_benchmark
        orm.tech_stack = company.tech_stack

        await self._session.flush()
        return CompanyMapper.to_domain(orm)

    async def list_companies(self, limit: int = 50, offset: int = 0) -> list[Company]:
        stmt = select(CompanyORM).offset(offset).limit(limit).order_by(CompanyORM.name.asc())
        res = await self._session.execute(stmt)
        orms = res.scalars().all()
        return [CompanyMapper.to_domain(o) for o in orms]
