"""
intelligence/ranking/semantic_scorer.py

SemanticScorer — computes cosine similarity between stored job vector embeddings
and candidate profile vector embeddings.
"""
from __future__ import annotations
import math
from typing import Optional, TYPE_CHECKING
from core.interfaces.repository import EmbeddingRepository

if TYPE_CHECKING:
    from core.models.candidate_profile import CandidateProfile
    from intelligence.embeddings.provider import LocalEmbeddingProvider


def build_candidate_profile_text(profile: CandidateProfile) -> str:
    """
    Constructs deterministic text representation of candidate profile for embedding.
    Combines target roles, technical skills, experience bullets, and background.
    """
    parts = []
    if profile.ideal_role_keywords:
        parts.append(f"Target Roles: {', '.join(profile.ideal_role_keywords)}")
    if profile.required_tech_stack:
        parts.append(f"Technical Skills: {', '.join(profile.required_tech_stack)}")
    if profile.experience_bullets:
        bullets = ' '.join(profile.experience_bullets[:5])
        parts.append(f"Experience: {bullets}")
    if profile.education_summary:
        parts.append(f"Education: {profile.education_summary}")
    if profile.target_locations:
        parts.append(f"Locations: {', '.join(profile.target_locations)}")

    text = ". ".join(parts).strip()
    return text or f"Software Engineer Profile: {profile.name}"


async def generate_candidate_vector(
    profile: CandidateProfile,
    provider: LocalEmbeddingProvider,
) -> list[float]:
    """Generates 384-d normalized float vector from candidate profile."""
    text = build_candidate_profile_text(profile)
    vectors = await provider.embed([text])
    return vectors[0] if vectors else []


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors, scaled to [0.0, 1.0]."""
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.5
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.5
    cos_sim = dot / (norm1 * norm2)
    # Scale from [-1.0, 1.0] to [0.0, 1.0]
    scaled = (cos_sim + 1.0) / 2.0
    return max(0.0, min(1.0, round(scaled, 4)))


class SemanticScorer:
    """
    Computes semantic similarity score for a job using its embedding_id
    and a candidate profile embedding vector.
    """

    def __init__(
        self,
        candidate_vector: Optional[list[float]] = None,
        embedding_repo: Optional[EmbeddingRepository] = None,
        preloaded_embeddings: Optional[dict[str, list[float]]] = None,
    ):
        self._candidate_vector = candidate_vector
        self._embedding_repo = embedding_repo
        self._cache: dict[str, list[float]] = dict(preloaded_embeddings or {})

    def set_candidate_vector(self, vector: list[float]) -> None:
        """Sets or updates the candidate embedding vector."""
        self._candidate_vector = vector

    def cache_vector(self, embedding_id: str, vector: list[float]) -> None:
        """Cache a job vector in memory."""
        if embedding_id and vector:
            self._cache[embedding_id] = vector

    async def score_async(self, embedding_id: str) -> float:
        """Asynchronously fetch embedding from repo and compute similarity."""
        if not embedding_id or not self._candidate_vector:
            return 0.5

        vector = self._cache.get(embedding_id)
        if vector is None and self._embedding_repo is not None:
            record = await self._embedding_repo.get_by_id(embedding_id)
            if record and record.get("vector"):
                vector = record["vector"]
                self._cache[embedding_id] = vector

        if vector is None:
            return 0.5

        return cosine_similarity(self._candidate_vector, vector)

    def score(self, embedding_id: str, job_vector: Optional[list[float]] = None) -> float:
        """Synchronously score embedding using cached vector or direct job_vector."""
        if not self._candidate_vector:
            return 0.5

        vector = job_vector or self._cache.get(embedding_id)
        if vector is None:
            return 0.5

        return cosine_similarity(self._candidate_vector, vector)
