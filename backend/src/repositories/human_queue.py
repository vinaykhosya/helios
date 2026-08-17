"""
backend/src/repositories/human_queue.py

SQLAlchemyHumanQueueRepository implementation.
Enforces domain state transitions and metadata updates.
"""
from __future__ import annotations
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.human_queue import HumanQueueEntry
from database.models.human_queue import HumanQueueORM


class SQLAlchemyHumanQueueRepository:

    def __init__(self, session: AsyncSession):
        self._session = session

    @property
    def session(self) -> AsyncSession:
        return self._session

    async def enqueue(self, entry: HumanQueueEntry) -> HumanQueueEntry:
        if entry.decision != "pending":
            raise ValueError(f"enqueue() requires decision='pending', got '{entry.decision}'")
        orm = self._to_orm(entry)
        self._session.add(orm)
        await self._session.flush()
        return self._to_domain(orm)

    async def enqueue_within_transaction(self, entry: HumanQueueEntry) -> HumanQueueEntry:
        """Enqueue entry inside an existing open transaction block without explicit commit."""
        return await self.enqueue(entry)

    async def decide(self, entry_id: str, new_decision: str) -> HumanQueueEntry:
        """Validate and apply state transition. Raises ValueError on invalid transition."""
        orm = await self._fetch(entry_id)
        domain = self._to_domain(orm)
        updated = domain.transition_to(new_decision)   # raises ValueError if invalid
        orm.decision = updated.decision
        orm.decided_at = updated.decided_at or datetime.utcnow()
        await self._session.flush()
        return self._to_domain(orm)

    async def set_telegram_pending_id(self, entry_id: str, pending_id: str) -> HumanQueueEntry:
        """
        Update telegram_pending_id metadata ONLY.
        Does NOT change decision state. Does NOT call transition_to().
        """
        orm = await self._fetch(entry_id)
        orm.telegram_pending_id = pending_id
        await self._session.flush()
        return self._to_domain(orm)

    async def mark_sheets_synced(self, entry_id: str) -> None:
        await self._session.execute(
            update(HumanQueueORM)
            .where(HumanQueueORM.id == entry_id)
            .values(sheets_row_synced=True, sheets_last_sync_at=datetime.utcnow())
        )
        await self._session.flush()

    async def expire_stale(self, ttl_hours: int = 48) -> int:
        cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)
        res = await self._session.execute(
            select(HumanQueueORM).where(
                HumanQueueORM.decision == "pending",
                HumanQueueORM.created_at < cutoff,
            )
        )
        stale = res.scalars().all()
        for orm in stale:
            orm.decision = "expired"
            orm.decided_at = datetime.utcnow()
        await self._session.flush()
        return len(stale)

    async def get_by_id(self, entry_id: str) -> Optional[HumanQueueEntry]:
        orm = await self._fetch_or_none(entry_id)
        return self._to_domain(orm) if orm else None

    async def get_by_application_id(self, application_id: str) -> Optional[HumanQueueEntry]:
        """Used by mark-applied endpoint to close the queue entry."""
        res = await self._session.execute(
            select(HumanQueueORM).where(HumanQueueORM.application_id == application_id)
        )
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_by_telegram_pending_id(self, pending_id: str) -> Optional[HumanQueueEntry]:
        res = await self._session.execute(
            select(HumanQueueORM).where(HumanQueueORM.telegram_pending_id == pending_id)
        )
        orm = res.scalar_one_or_none()
        return self._to_domain(orm) if orm else None

    async def get_pending(self, user_id: str) -> list[HumanQueueEntry]:
        res = await self._session.execute(
            select(HumanQueueORM)
            .where(HumanQueueORM.user_id == user_id, HumanQueueORM.decision == "pending")
            .order_by(HumanQueueORM.created_at.desc())
        )
        return [self._to_domain(o) for o in res.scalars().all()]

    async def list_all(
        self, user_id: str, decision: Optional[str] = None, limit: int = 50
    ) -> list[HumanQueueEntry]:
        stmt = (
            select(HumanQueueORM)
            .where(HumanQueueORM.user_id == user_id)
        )
        if decision:
            stmt = stmt.where(HumanQueueORM.decision == decision)
        stmt = stmt.order_by(HumanQueueORM.created_at.desc()).limit(limit)
        res = await self._session.execute(stmt)
        return [self._to_domain(o) for o in res.scalars().all()]

    async def _fetch(self, entry_id: str) -> HumanQueueORM:
        orm = await self._fetch_or_none(entry_id)
        if orm is None:
            raise LookupError(f"HumanQueueEntry not found: {entry_id}")
        return orm

    async def _fetch_or_none(self, entry_id: str) -> Optional[HumanQueueORM]:
        res = await self._session.execute(
            select(HumanQueueORM).where(HumanQueueORM.id == entry_id)
        )
        return res.scalar_one_or_none()

    @staticmethod
    def _to_domain(orm: HumanQueueORM) -> HumanQueueEntry:
        return HumanQueueEntry(
            id=orm.id,
            user_id=orm.user_id,
            job_id=orm.job_id,
            application_id=orm.application_id,
            telegram_pending_id=orm.telegram_pending_id,
            telegram_message_id=orm.telegram_message_id,
            decision=orm.decision,
            fit_score=float(orm.fit_score) if orm.fit_score is not None else None,
            confidence_score=float(orm.confidence_score) if orm.confidence_score is not None else None,
            friction_score=orm.friction_score or 0,
            routing_reason=orm.routing_reason,
            resume_path=orm.resume_path,
            application_url=orm.application_url,
            matching_skills=orm.matching_skills or [],
            missing_skills=orm.missing_skills or [],
            created_at=orm.created_at,
            decided_at=orm.decided_at,
            expires_at=orm.expires_at,
            sheets_row_synced=orm.sheets_row_synced or False,
        )

    @staticmethod
    def _to_orm(entry: HumanQueueEntry) -> HumanQueueORM:
        return HumanQueueORM(
            id=entry.id,
            user_id=entry.user_id,
            job_id=entry.job_id,
            application_id=entry.application_id,
            telegram_pending_id=entry.telegram_pending_id,
            telegram_message_id=entry.telegram_message_id,
            decision=entry.decision,
            fit_score=entry.fit_score,
            confidence_score=entry.confidence_score,
            friction_score=entry.friction_score,
            routing_reason=entry.routing_reason,
            resume_path=entry.resume_path,
            application_url=entry.application_url,
            matching_skills=entry.matching_skills,
            missing_skills=entry.missing_skills,
            created_at=entry.created_at,
            decided_at=entry.decided_at,
            expires_at=entry.expires_at,
            sheets_row_synced=entry.sheets_row_synced,
        )
