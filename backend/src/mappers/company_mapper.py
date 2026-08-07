"""
backend/src/mappers/company_mapper.py

Maps between Company Pydantic Domain Model and CompanyORM database model.
"""
from __future__ import annotations

from core.models.company import Company, CompanySize
from database.models.company import CompanyORM


class CompanyMapper:
    """Translation layer between Company domain and database models."""

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
    def to_domain(orm: CompanyORM) -> Company:
        """Map CompanyORM instance to Company domain model."""
        size = CompanySize(orm.size) if orm.size else None
        tech_stack = CompanyMapper._parse_list(orm.tech_stack)
        return Company(
            id=orm.id,
            schema_version=1,
            name=orm.name,
            website=orm.website,
            industry=orm.industry,
            size=size,
            description=orm.description,
            logo_url=orm.logo_url,
            linkedin_url=orm.linkedin_url,
            glassdoor_url=orm.glassdoor_url,
            headquarters=orm.headquarters,
            founded_year=orm.founded_year,
            salary_benchmark=orm.salary_data,
            tech_stack=tech_stack,
            embedding_id=None,
        )

    @staticmethod
    def to_orm(domain: Company) -> CompanyORM:
        """Map Company domain model to CompanyORM instance."""
        return CompanyORM(
            id=domain.id,
            name=domain.name,
            name_normalized=domain.name.lower().strip(),
            website=domain.website,
            industry=domain.industry,
            size=domain.size,
            description=domain.description,
            logo_url=domain.logo_url,
            linkedin_url=domain.linkedin_url,
            glassdoor_url=domain.glassdoor_url,
            headquarters=domain.headquarters,
            founded_year=domain.founded_year,
            salary_data=domain.salary_benchmark,
            tech_stack=domain.tech_stack,
        )
