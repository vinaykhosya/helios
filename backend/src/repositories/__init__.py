"""
backend/src/repositories/__init__.py

Exposes concrete SQLAlchemy repository implementations.
"""
from backend.src.repositories.job import SQLAlchemyJobRepository
from backend.src.repositories.company import SQLAlchemyCompanyRepository
from backend.src.repositories.application import SQLAlchemyApplicationRepository
from backend.src.repositories.user import SQLAlchemyUserRepository

__all__ = [
    "SQLAlchemyJobRepository",
    "SQLAlchemyCompanyRepository",
    "SQLAlchemyApplicationRepository",
    "SQLAlchemyUserRepository",
]
