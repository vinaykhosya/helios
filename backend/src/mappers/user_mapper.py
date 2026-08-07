"""
backend/src/mappers/user_mapper.py

Maps between User Pydantic Domain Model and UserORM database model.
"""
from __future__ import annotations

from core.models.user import User, UserSettings
from database.models.user import UserORM


class UserMapper:
    """Translation layer between User domain and database models."""

    @staticmethod
    def to_domain(orm: UserORM) -> User:
        """Map UserORM instance to User domain model."""
        settings = UserSettings(**orm.settings) if orm.settings else UserSettings()
        return User(
            id=orm.id,
            schema_version=1,
            email=orm.email,
            name=orm.name,
            profile=orm.profile,
            skills=orm.skills or [],
            target_roles=orm.target_roles or [],
            target_locations=orm.target_locations or [],
            settings=settings,
            embedding_id=None,
        )

    @staticmethod
    def to_orm(domain: User) -> UserORM:
        """Map User domain model to UserORM instance."""
        return UserORM(
            id=domain.id,
            email=domain.email,
            name=domain.name,
            profile=domain.profile,
            settings=domain.settings.model_dump(),
            skills=domain.skills,
            target_roles=domain.target_roles,
            target_locations=domain.target_locations,
        )
