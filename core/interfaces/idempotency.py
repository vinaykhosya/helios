"""
core/interfaces/idempotency.py

IdempotencyStrategy protocol and SourceUpdatedIdempotencyStrategy implementation.
"""
from __future__ import annotations

import hashlib
from typing import Protocol
from core.models.job import Job


class IdempotencyStrategy(Protocol):
    """Protocol for calculating ingestion idempotency keys."""

    version: int

    def compute_key(self, job: Job) -> str:
        """Compute the idempotency hash key for a job."""
        ...


class SourceUpdatedIdempotencyStrategy(IdempotencyStrategy):
    """
    Ingestion Idempotency Key calculation:
    SHA256(source + source_id + updated_at + strategy_version)
    """

    version = 1

    def compute_key(self, job: Job) -> str:
        # greenhouse updated_at or similar is in raw_data
        updated_at = job.raw_data.get("updated_at") or ""
        payload = f"{job.source}:{job.source_id}:{updated_at}:v{self.version}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()
