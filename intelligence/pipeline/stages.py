"""
intelligence/pipeline/stages.py

The Helios ingestion pipeline — stage contracts and execution order.

Every job that enters Helios passes through this pipeline in order.
No stage is optional. Each stage may enrich, filter, or annotate jobs.

Pipeline definition:

  Connector
    ↓
  [1] NormalizerStage       — validate, clean, coerce types
    ↓
  [2] DeduplicatorStage     — drop jobs already in the database
    ↓
  [3] CompanyResolverStage  — link job.company_name → Company record
    ↓
  [4] EmbeddingGeneratorStage — generate and store vector embeddings
    ↓
  [5] RankerStage           — score job against user profiles
    ↓
  [6] PersistenceStage      — write to database, fire events

Implementation phases:
  Phase 1: These contracts only.
  Phase 2: PersistenceStage (requires DB).
  Phase 3: NormalizerStage, DeduplicatorStage, CompanyResolverStage.
  Phase 4: EmbeddingGeneratorStage, RankerStage.
"""
from __future__ import annotations

from core.interfaces.pipeline_stage import BasePipelineStage
from core.interfaces.repository import JobRepository, CompanyRepository
from core.models.job import Job
from core.models.company import Company


from core.interfaces.idempotency import IdempotencyStrategy, SourceUpdatedIdempotencyStrategy


class NormalizerStage(BasePipelineStage):
    """
    Stage 1 — Validate and clean raw Job objects from connectors.

    Responsibilities:
      - Strip HTML tags from description fields
      - Normalize title casing and punctuation
      - Ensure required fields (title, company) are non-empty
      - Generate versioned idempotency key
    """

    name = "normalizer"

    def __init__(self, idempotency_strategy: Optional[IdempotencyStrategy] = None):
        self._idempotency_strategy = idempotency_strategy or SourceUpdatedIdempotencyStrategy()

    @staticmethod
    def strip_html(html_str: str) -> str:
        if not html_str:
            return ""
        import re
        # Remove tags without introducing space around inline tags, strip duplicate spaces
        clean = re.sub(r'<[^>]*>', '', html_str)
        return " ".join(clean.split())

    async def process(self, jobs: list[Job]) -> list[Job]:
        normalized = []
        for job in jobs:
            try:
                if not job.title or not job.company:
                    print(f"Normalizer dropping job: missing title or company. id={job.source_id}")
                    continue

                desc_clean = self.strip_html(job.description or "")
                
                # Ingestion idempotency key calculation via strategy wrapper
                idempotency_key = self._idempotency_strategy.compute_key(job)

                clean_job = job.model_copy(update={
                    "title": job.title.strip(),
                    "company": job.company.strip(),
                    "description": desc_clean,
                    "idempotency_key": idempotency_key,
                })
                normalized.append(clean_job)
            except Exception as e:
                print(f"Normalizer error: {e}")
        return normalized


class DeduplicatorStage(BasePipelineStage):
    """
    Stage 2 — Remove jobs already stored in the database.

    Phase 3 exact match strategy:
      - Looks up job by (source, source_id) in database.
      - If found: drops the job from the pipeline.
      - If not found: passes the job through.
    """

    name = "deduplicator"

    def __init__(self, job_repo: JobRepository):
        self._job_repo = job_repo

    async def process(self, jobs: list[Job]) -> list[Job]:
        unique_jobs = []
        for job in jobs:
            try:
                existing = await self._job_repo.get_by_source_id(job.source, job.source_id)
                if not existing:
                    unique_jobs.append(job)
            except Exception as e:
                print(f"Error checking deduplication for job '{job.title}': {e}")
                # Pass through unchanged on query error to preserve data safety
                unique_jobs.append(job)
        return unique_jobs


class CompanyResolverStage(BasePipelineStage):
    """
    Stage 3 — Link job.company to a Company record.

    For each job:
      1. Normalize company name (lowercase, stripped).
      2. Lookup by normalized name in the companies table.
      3. If found: set job.company_id.
      4. If not found: create a new Company record and set job.company_id.
    """

    name = "company_resolver"

    def __init__(self, company_repo: CompanyRepository):
        self._company_repo = company_repo

    async def process(self, jobs: list[Job]) -> list[Job]:
        resolved_jobs = []
        for job in jobs:
            try:
                norm_name = job.company.lower().strip()
                company = await self._company_repo.get_by_normalized_name(norm_name)
                if not company:
                    company = Company(name=job.company)
                    company = await self._company_repo.create(company)
                
                updated_job = job.model_copy(update={"company_id": company.id})
                resolved_jobs.append(updated_job)
            except Exception as e:
                print(f"Error resolving company for job '{job.title}': {e}")
                # Pass through unchanged per the interface specifications
                resolved_jobs.append(job)
        return resolved_jobs


class EmbeddingGeneratorStage(BasePipelineStage):
    """
    Stage 4 — Generate and store vector embeddings for each job.

    Input text for embedding:
      f"{job.title}. {job.description[:2000]}. Skills: {', '.join(job.skills)}"

    Process:
      1. Call the configured embedding provider (OpenAI text-embedding-3-small or equivalent).
      2. Store the vector in the job_embeddings table.
      3. Set job.embedding_id to the stored record's ID.

    Used by RankerStage to compute cosine similarity against user embeddings.
    Phase 4 implementation (requires pgvector and an embedding provider).
    """

    name = "embedding_generator"

    async def process(self, jobs: list[Job]) -> list[Job]:
        raise NotImplementedError("EmbeddingGeneratorStage is implemented in Phase 4.")


class RankerStage(BasePipelineStage):
    """
    Stage 5 — Score each job against all active user profiles.

    Ranking is not purely AI. It combines:
      - Vector similarity: cosine(job_embedding, user_embedding) → base score
      - Rule-based boosts:
          +0.10 if job.city matches user.target_locations
          +0.05 if job.remote matches user.settings.preferred_remote
          +0.05 if seniority aligns with profile experience level
      - LLM re-ranking for top candidates (Phase 4+, expensive — apply sparingly)

    Output:
      - Sets job.fit_score per user (stored in a user_job_scores join table).
      - Fires JobRanked event for scores ≥ user notification threshold.

    Phase 4 implementation.
    """

    name = "ranker"

    async def process(self, jobs: list[Job]) -> list[Job]:
        raise NotImplementedError("RankerStage is implemented in Phase 4.")




class PersistenceStage(BasePipelineStage):
    """
    Stage 6 — Write jobs and their derived data to the database.

    For each job:
      1. Upserts the jobs record (update if source+source_id exists).
    """

    name = "persistence"

    def __init__(self, job_repo: JobRepository):
        self._job_repo = job_repo

    async def process(self, jobs: list[Job]) -> list[Job]:
        persisted_jobs = []
        for job in jobs:
            try:
                # Check if job already exists
                existing = await self._job_repo.get_by_source_id(job.source, job.source_id)
                if existing:
                    job_to_persist = job.model_copy(update={"id": existing.id})
                    updated = await self._job_repo.update(job_to_persist)
                    persisted_jobs.append(updated)
                else:
                    created = await self._job_repo.create(job)
                    persisted_jobs.append(created)
            except Exception as e:
                # Per the interface rule: "Never raises. Individual job failures are logged and that
                # job is either dropped or passed through unchanged."
                print(f"Error persisting job '{job.title}': {e}")
        return persisted_jobs


# ── Pipeline definition ───────────────────────────────────────────────────────

INGESTION_PIPELINE: list[type[BasePipelineStage]] = [
    NormalizerStage,
    DeduplicatorStage,
    CompanyResolverStage,
    EmbeddingGeneratorStage,
    RankerStage,
    PersistenceStage,
]
"""
The canonical Helios ingestion pipeline.

Stages are instantiated and executed in this order by the ingestion worker.
Reorder only with an ADR — pipeline stage order is architecture.
"""
