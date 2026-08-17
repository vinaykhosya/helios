"""
backend/src/repositories/embedding.py

SQLAlchemyEmbeddingRepository — concrete implementation of EmbeddingRepository.
Stores and retrieves vector embeddings from PostgreSQL / SQLite.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.interfaces.repository import EmbeddingRepository
from database.models.job import JobEmbeddingORM


class SQLAlchemyEmbeddingRepository(EmbeddingRepository):

    def __init__(self, session: AsyncSession):
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def store(
        self,
        entity_id: str,
        embedding_id: str,
        vector: list[float],
        model: str,
    ) -> None:
        """Store or update embedding vector in database."""
        stmt = select(JobEmbeddingORM).where(JobEmbeddingORM.id == embedding_id)
        res = await self._session.execute(stmt)
        existing = res.scalar_one_or_none()

        if existing:
            existing.embedding = vector
            existing.model = model
            existing.created_at = datetime.utcnow()
        else:
            orm = JobEmbeddingORM(
                id=embedding_id,
                job_id=entity_id,
                model=model,
                embedding=vector,
                created_at=datetime.utcnow(),
            )
            self._session.add(orm)

        await self._session.flush()

    async def get_by_id(self, embedding_id: str) -> Optional[dict]:
        """Retrieve stored embedding vector by embedding UUID."""
        stmt = select(JobEmbeddingORM).where(JobEmbeddingORM.id == embedding_id)
        res = await self._session.execute(stmt)
        orm = res.scalar_one_or_none()
        if not orm:
            return None
        return {
            "id": orm.id,
            "job_id": orm.job_id,
            "model": orm.model,
            "vector": [float(x) for x in orm.embedding] if orm.embedding is not None else [],
            "created_at": orm.created_at,
        }

    async def get_by_job_id(self, job_id: str) -> Optional[dict]:
        """Retrieve stored embedding vector by job UUID."""
        stmt = select(JobEmbeddingORM).where(JobEmbeddingORM.job_id == job_id).order_by(JobEmbeddingORM.created_at.desc())
        res = await self._session.execute(stmt)
        orm = res.scalars().first()
        if not orm:
            return None
        return {
            "id": orm.id,
            "job_id": orm.job_id,
            "model": orm.model,
            "vector": [float(x) for x in orm.embedding] if orm.embedding is not None else [],
            "created_at": orm.created_at,
        }

