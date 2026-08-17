"""
backend/src/api/deps.py

Common FastAPI dependency providers for authentication, user context, and database sessions.
"""
from __future__ import annotations
import os
from typing import AsyncGenerator
from fastapi import Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.core.di import DIContainer


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yields an active database AsyncSession from DIContainer."""
    async with DIContainer.session() as session:
        yield session


def get_current_user_id(
    request: Request,
    x_user_id: str | None = Header(None, alias="X-User-ID"),
) -> str:
    """
    Extracts the authenticated user ID.
    Defaults to X-User-ID header if provided, or HELIOS_DEFAULT_USER_ID, or 'user_default'.
    Provides a clean extension point for JWT/OAuth without changing endpoint signatures.
    """
    return x_user_id or os.getenv("HELIOS_DEFAULT_USER_ID", "user_default")
