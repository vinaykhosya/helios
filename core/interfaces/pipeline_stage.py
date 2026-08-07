"""
core/interfaces/pipeline_stage.py

BasePipelineStage — the contract for every stage in the Helios ingestion pipeline.

Pipeline execution order (defined in intelligence/pipeline/stages.py):

  Connector
    ↓
  NormalizerStage       — validate, clean, coerce types
    ↓
  DeduplicatorStage     — drop jobs already in the database
    ↓
  CompanyResolverStage  — link job.company_name → Company record
    ↓
  EmbeddingGeneratorStage — generate and store vector embeddings
    ↓
  RankerStage           — score job against user profiles
    ↓
  PersistenceStage      — write to database, fire events

Each stage receives a list[Job] and returns a list[Job].
Stages may filter (deduplicator), enrich (embeddings), or annotate (ranker).
Stages must never raise on individual job failures — log and skip.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from core.models.job import Job


class BasePipelineStage(ABC):
    """
    One stage in the Helios job ingestion pipeline.

    Stages are stateless transforms. All state (DB, cache, etc.)
    is injected via the constructor in concrete implementations.
    """

    #: Stage identifier for logging and metrics, e.g. "normalizer".
    name: str

    @abstractmethod
    async def process(self, jobs: list[Job]) -> list[Job]:
        """
        Transform the input job list and return the result.

        A stage may:
          - Return the same list (validation / annotation stages)
          - Return a shorter list (deduplication / filtering stages)
          - Return an enriched list (embedding / company resolver stages)

        Guarantees:
          - Never raises. Individual job failures are logged and that
            job is either dropped or passed through unchanged.
          - Always returns a list[Job], even if empty.
          - Does not mutate the input list in place; return new objects
            or copies where fields are changed.

        Args:
            jobs: List of Job objects from the previous stage.

        Returns:
            Transformed list of Job objects for the next stage.
        """
        ...
