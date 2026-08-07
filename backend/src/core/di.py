"""
backend/src/core/di.py

Helios Dependency Injection Container.
Allows registering and resolving database engines, repositories, and services.
Unifies DI for FastAPI web endpoints and standalone background event workers.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.interfaces.repository import (
    JobRepository,
    CompanyRepository,
    ApplicationRepository,
    UserRepository,
)
from backend.src.repositories.job import SQLAlchemyJobRepository
from backend.src.repositories.company import SQLAlchemyCompanyRepository
from backend.src.repositories.application import SQLAlchemyApplicationRepository
from backend.src.repositories.user import SQLAlchemyUserRepository

T = TypeVar("T")


class DIContainer:
    """
    Helios Dependency Injection Container.
    Holds database connection state and handles repository/service instantiation.
    """

    _engine: Optional[AsyncEngine] = None
    _session_maker: Optional[async_sessionmaker[AsyncSession]] = None

    # Implement custom container bindings mapping Protocols to concrete implementations
    _bindings: dict[type, type] = {
        JobRepository: SQLAlchemyJobRepository,
        CompanyRepository: SQLAlchemyCompanyRepository,
        ApplicationRepository: SQLAlchemyApplicationRepository,
        UserRepository: SQLAlchemyUserRepository,
    }

    @classmethod
    def initialize(cls, database_url: Optional[str] = None) -> None:
        """Initialize the database engine and session maker."""
        if cls._engine is not None:
            return  # already initialized

        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL must be provided or set in environment variables")

        cls._engine = create_async_engine(url, echo=False, pool_pre_ping=True)
        cls._session_maker = async_sessionmaker(
            bind=cls._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @classmethod
    async def shutdown(cls) -> None:
        """Dispose of the database engine."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_maker = None

    @classmethod
    @asynccontextmanager
    async def session(cls) -> AsyncGenerator[AsyncSession, None]:
        """Context manager yielding a fresh database AsyncSession."""
        if cls._session_maker is None:
            raise RuntimeError("DIContainer is not initialized. Call initialize() first.")
        async with cls._session_maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise
            finally:
                await s.close()

    @classmethod
    def resolve_repository(cls, interface: Type[T], session: AsyncSession) -> T:
        """Resolve a repository interface to its bound concrete implementation."""
        concrete_type = cls._bindings.get(interface)
        if concrete_type is None:
            raise KeyError(f"No concrete class bound to interface {interface.__name__}")
        return concrete_type(session)
