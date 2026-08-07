"""
backend/src/api/companies.py

FastAPI route handlers for Company operations.
Exposes CRUD endpoints resolved via DIContainer.
"""
from __future__ import annotations

from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.company import Company
from core.interfaces.repository import CompanyRepository
from backend.src.core.di import DIContainer
from backend.src.services.company_service import CompanyService

router = APIRouter(prefix="/api/v1/companies", tags=["Companies"])


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for database session lifecycle management."""
    async with DIContainer.session() as session:
        yield session


def get_company_service(session: AsyncSession = Depends(get_db_session)) -> CompanyService:
    """FastAPI Dependency for resolving CompanyService with injected repository protocols."""
    company_repo = DIContainer.resolve_repository(CompanyRepository, session)
    return CompanyService(company_repo)


@router.post("", response_model=Company, status_code=status.HTTP_201_CREATED)
async def create_company(company: Company, service: CompanyService = Depends(get_company_service)) -> Company:
    """Create a new company profile. Normalizes name to prevent duplication."""
    return await service.create_company(company)


@router.get("", response_model=list[Company])
async def list_companies(
    limit: int = 50,
    offset: int = 0,
    service: CompanyService = Depends(get_company_service),
) -> list[Company]:
    """Retrieve a list of company profiles ordered alphabetically."""
    return await service.list_companies(limit=limit, offset=offset)


@router.get("/{company_id}", response_model=Company)
async def get_company(company_id: str, service: CompanyService = Depends(get_company_service)) -> Company:
    """Retrieve a single company profile by its UUID."""
    company = await service.get_company(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company not found: {company_id}",
        )
    return company
