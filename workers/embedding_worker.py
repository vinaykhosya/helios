"""
workers/embedding_worker.py

EmbeddingWorker — subscribes to JobPersisted, generates a semantic embedding,
stores it, and emits EmbeddingGenerated so WorkflowOrchestrator can proceed to ranking.

Event chain this worker participates in:
  JobPersisted  <- [EmbeddingWorker] ->  EmbeddingGenerated
                                              |
                                    WorkflowOrchestrator.handle_embedding_generated()

Invariants enforced:
  - Subscribes to "JobPersisted" ONLY. Never subscribes to "JobDiscovered".
  - Always emits EmbeddingGenerated, even on failure (with embedding_id="" as fallback).
  - A failure here never crashes the pipeline; it degrades to semantic_score=0.5.
  - embedding_id="" explicitly signals "semantic data unavailable" to downstream consumers.
"""
from __future__ import annotations

import uuid
from typing import Optional

from core.events.definitions import EmbeddingGenerated, JobPersisted
from core.interfaces.event_bus import EventBus


class EmbeddingWorker:
    """
    Subscribes to JobPersisted. Generates and stores a vector embedding for each
    persisted job, then emits EmbeddingGenerated for WorkflowOrchestrator.

    embedding_provider: any object with async embed(texts: list[str]) -> list[list[float]].
                        If None, all jobs receive embedding_id="" (Phase 0 behaviour).
    job_repo:           used to fetch the full job (title + description) for embedding text.
                        If None, embedding text falls back to source_url.
    embedding_repo:     used to persist the vector. If None, vector is generated but not stored.
    """

    def __init__(
        self,
        event_bus: EventBus,
        embedding_provider=None,
        job_repo=None,
        embedding_repo=None,
    ):
        self._bus = event_bus
        self._embedding_provider = embedding_provider
        self._job_repo = job_repo
        self._embedding_repo = embedding_repo

        # INVARIANT #2: subscribe to JobPersisted ONLY
        self._bus.subscribe("JobPersisted", self.handle_job_persisted)

    async def handle_job_persisted(self, event: JobPersisted) -> None:
        """
        Main handler. Generates and stores embedding, emits EmbeddingGenerated.
        Always emits -- never raises. Failures produce embedding_id="" (semantic fallback).
        """
        embedding_id: str = ""

        try:
            embedding_id = await self._generate_and_store(event)
        except Exception as exc:
            print(
                f"[EmbeddingWorker] Failed to generate embedding for job={event.job_id}: "
                f"{type(exc).__name__}: {exc}"
            )
            embedding_id = ""

        await self._bus.publish(EmbeddingGenerated(
            entity_type="job",
            entity_id=event.job_id,
            model=getattr(self._embedding_provider, "model_name", "none"),
            embedding_id=embedding_id,
            correlation_id=event.correlation_id,
        ))

    async def _generate_and_store(self, event: JobPersisted) -> str:
        """
        Generate embedding text, call provider, store result.
        Returns the embedding_id UUID string if successful.
        Returns "" if provider is not wired (Phase 0 / test mode).
        """
        if self._embedding_provider is None:
            return ""

        embedding_text = await self._build_embedding_text(event)
        vectors = await self._embedding_provider.embed([embedding_text])
        vector = vectors[0]

        embedding_id = str(uuid.uuid4())
        if self._embedding_repo is not None:
            await self._embedding_repo.store(
                entity_id=event.job_id,
                embedding_id=embedding_id,
                vector=vector,
                model=self._embedding_provider.model_name,
            )

        return embedding_id

    async def _build_embedding_text(self, event: JobPersisted) -> str:
        """Build the text string to embed for a job."""
        if self._job_repo is not None:
            job = await self._job_repo.get_by_id(event.job_id)
            if job:
                title = getattr(job, "title", "") or ""
                description = (getattr(job, "description", "") or "")[:512]
                company = getattr(job, "company", "") or ""
                return f"{title} at {company}. {description}".strip()
        return f"Job at {event.source_url}"
