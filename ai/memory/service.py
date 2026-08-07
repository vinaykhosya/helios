"""
ai/memory/service.py

MemoryService — Shared stateful store & brain for all Helios agents.
Provides fast caching via Redis and persistent storage via PostgreSQL repositories.
"""
from __future__ import annotations

import hashlib
from typing import Optional
from pydantic import BaseModel, Field

from core.interfaces.repository import ApplicationRepository, JobRepository


class QuestionnaireAnswer(BaseModel):
    question_text: str
    question_hash: str
    answer: str


class MemoryService:
    """
    Shared memory service for deduplication, portal Q&A retention, resume analytics, and outcome tracking.
    """

    def __init__(
        self,
        application_repo: Optional[ApplicationRepository] = None,
        job_repo: Optional[JobRepository] = None,
        redis_client: Optional[object] = None,
    ):
        self.app_repo = application_repo
        self.job_repo = job_repo
        self.redis = redis_client
        self._in_memory_qa: dict[str, str] = {}
        self._in_memory_applied: set[str] = set()

    @staticmethod
    def hash_question(question_text: str) -> str:
        """Normalized SHA256 hash for Q&A matching."""
        norm = " ".join(question_text.lower().strip().split())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]

    async def has_applied(self, job_id: str, user_id: str) -> bool:
        """
        Checks if candidate has already applied to this job.
        Checks in-memory/Redis cache first before hitting repository.
        """
        cache_key = f"applied:{user_id}:{job_id}"
        if cache_key in self._in_memory_applied:
            return True

        if self.redis is not None:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    self._in_memory_applied.add(cache_key)
                    return True
            except Exception:
                pass

        if self.app_repo is not None:
            existing = await self.app_repo.get_by_user_and_job(user_id, job_id)
            if existing:
                self._in_memory_applied.add(cache_key)
                if self.redis is not None:
                    try:
                        await self.redis.setex(cache_key, 90 * 86400, "1")
                    except Exception:
                        pass
                return True

        return False

    async def record_application(
        self,
        job_id: str,
        user_id: str,
        confirmation_id: Optional[str] = None,
        resume_version: Optional[str] = None,
        confidence_score: float = 1.0,
    ) -> None:
        """
        Records a submitted application into memory and Redis cache.
        """
        cache_key = f"applied:{user_id}:{job_id}"
        self._in_memory_applied.add(cache_key)
        if self.redis is not None:
            try:
                await self.redis.setex(cache_key, 90 * 86400, "1")
            except Exception:
                pass

    async def get_standard_answer(self, question_text: str) -> Optional[str]:
        """
        Retrieves saved answer for a portal questionnaire prompt.
        """
        q_hash = self.hash_question(question_text)
        if q_hash in self._in_memory_qa:
            return self._in_memory_qa[q_hash]

        if self.redis is not None:
            try:
                val = await self.redis.get(f"qa:{q_hash}")
                if val:
                    val_str = val.decode("utf-8") if isinstance(val, bytes) else str(val)
                    self._in_memory_qa[q_hash] = val_str
                    return val_str
            except Exception:
                pass

        return None

    async def store_standard_answer(self, question_text: str, answer: str) -> None:
        """
        Stores an answer for a portal question to reuse across future applications.
        """
        q_hash = self.hash_question(question_text)
        self._in_memory_qa[q_hash] = answer
        if self.redis is not None:
            try:
                await self.redis.set(f"qa:{q_hash}", answer)
            except Exception:
                pass
