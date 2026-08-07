"""
backend/src/repositories/user.py

SQLAlchemyUserRepository concrete implementation of core.interfaces.UserRepository.
Converts ORM model (UserORM) instances to/from Domain Pydantic models (User).
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.models.user import User
from core.interfaces.repository import UserRepository
from database.models.user import UserORM
from backend.src.mappers.user_mapper import UserMapper


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of the UserRepository protocol."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, user: User) -> User:
        orm = UserMapper.to_orm(user)
        self._session.add(orm)
        await self._session.flush()
        return UserMapper.to_domain(orm)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        stmt = select(UserORM).where(UserORM.id == user_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return UserMapper.to_domain(orm) if orm else None

    async def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(UserORM).where(UserORM.email == email)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        return UserMapper.to_domain(orm) if orm else None

    async def update(self, user: User) -> User:
        stmt = select(UserORM).where(UserORM.id == user.id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if not orm:
            from core.exceptions import UserNotFoundError
            raise UserNotFoundError(f"User not found for update: {user.id}")

        orm.email = user.email
        orm.name = user.name
        orm.profile = user.profile
        orm.settings = user.settings.model_dump()
        orm.skills = user.skills
        orm.target_roles = user.target_roles
        orm.target_locations = user.target_locations

        await self._session.flush()
        return UserMapper.to_domain(orm)
