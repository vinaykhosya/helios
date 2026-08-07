"""
workers/ingestion_worker.py

IngestionWorker class (synchronous worker runtime).
Subscribes to JobDiscovered events, executes the pipeline stages, and commits jobs to the database.
"""
from __future__ import annotations

from core.events.definitions import JobDiscovered
from core.interfaces.event_bus import EventBus
from core.interfaces.repository import JobRepository, CompanyRepository
from core.models.job import Job, JobSource
from intelligence.pipeline.stages import (
    NormalizerStage,
    DeduplicatorStage,
    CompanyResolverStage,
    PersistenceStage,
)


class IngestionWorker:
    """Synchronous in-process worker that reacts to JobDiscovered events and executes ingestion."""

    def __init__(self, event_bus: EventBus, job_repo: JobRepository, company_repo: CompanyRepository):
        self._event_bus = event_bus
        self._job_repo = job_repo
        self._company_repo = company_repo

        # Register pub/sub subscriber
        self._event_bus.subscribe("JobDiscovered", self.handle_job_discovered)

    async def handle_job_discovered(self, event: JobDiscovered) -> None:
        """Pipeline orchestrator fired on JobDiscovered event."""
        raw_job = event.metadata.get("raw_job")
        if not raw_job:
            return

        # Translate raw JSON format (e.g. dict from connector) or accept model
        if isinstance(raw_job, dict):
            # Safe parsing of Greenhouse payload structure
            company_name = (
                raw_job.get("company", {}).get("name")
                if isinstance(raw_job.get("company"), dict)
                else raw_job.get("company")
            ) or "Unknown Company"

            job_model = Job(
                source=JobSource(event.source),
                source_id=event.source_id,
                source_url=event.source_url,
                title=raw_job.get("title", "Untitled Job"),
                company=company_name,
                description=raw_job.get("content", ""),
                raw_data=raw_job,
            )
        elif isinstance(raw_job, Job):
            job_model = raw_job
        else:
            return

        # Instantiate pipeline stages
        normalizer = NormalizerStage()
        deduplicator = DeduplicatorStage(self._job_repo)
        resolver = CompanyResolverStage(self._company_repo)
        persistence = PersistenceStage(self._job_repo)

        # Run pipeline stages sequentially
        jobs = [job_model]
        jobs = await normalizer.process(jobs)
        jobs = await deduplicator.process(jobs)
        jobs = await resolver.process(jobs)
        await persistence.process(jobs)
