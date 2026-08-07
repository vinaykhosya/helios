"""
backend/src/services/company_service.py

CompanyService implements business logic for Company records.
Interacts with the database purely via CompanyRepository interface.
"""
from __future__ import annotations

from typing import Optional
from core.models.company import Company
from core.interfaces.repository import CompanyRepository


class CompanyService:
    """Service class for managing Company operations."""

    def __init__(self, company_repo: CompanyRepository):
        self._repo = company_repo

    async def create_company(self, company: Company) -> Company:
        """Create a new company record. Normalizes names for deduping."""
        normalized_name = company.name.lower().strip()
        existing = await self._repo.get_by_normalized_name(normalized_name)
        if existing:
            return existing  # return existing if name matches normalized check
        return await self._repo.create(company)

    async def get_company(self, company_id: str) -> Optional[Company]:
        """Retrieve a company by its ID."""
        return await self._repo.get_by_id(company_id)

    async def list_companies(self, limit: int = 50, offset: int = 0) -> list[Company]:
        """Retrieve a list of companies ordered alphabetically."""
        return await self._repo.list_companies(limit=limit, offset=offset)
