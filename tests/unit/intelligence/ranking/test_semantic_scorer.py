"""
tests/unit/intelligence/ranking/test_semantic_scorer.py

Unit tests for SemanticScorer and cosine_similarity function.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from intelligence.ranking.semantic_scorer import SemanticScorer, cosine_similarity


def test_cosine_similarity_identical_vectors():
    vec = [0.6, 0.8, 0.0]
    sim = cosine_similarity(vec, vec)
    assert sim == 1.0


def test_cosine_similarity_opposite_vectors():
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [-1.0, 0.0, 0.0]
    sim = cosine_similarity(vec1, vec2)
    assert sim == 0.0


def test_cosine_similarity_orthogonal_vectors():
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [0.0, 1.0, 0.0]
    sim = cosine_similarity(vec1, vec2)
    assert sim == 0.5


def test_cosine_similarity_mismatched_dimensions_fallback():
    assert cosine_similarity([1.0, 2.0], [1.0]) == 0.5
    assert cosine_similarity([], []) == 0.5


def test_semantic_scorer_with_preloaded_vectors():
    candidate_vec = [1.0, 0.0, 0.0]
    job_vec = [0.8, 0.6, 0.0]  # dot product = 0.8 -> scaled = (0.8 + 1) / 2 = 0.9

    scorer = SemanticScorer(
        candidate_vector=candidate_vec,
        preloaded_embeddings={"emb-1": job_vec},
    )

    score = scorer.score("emb-1")
    assert score == 0.9

    # Unknown embedding ID falls back to 0.5
    assert scorer.score("unknown-emb") == 0.5


@pytest.mark.asyncio
async def test_semantic_scorer_async_with_repo():
    candidate_vec = [1.0, 0.0, 0.0]
    job_vec = [1.0, 0.0, 0.0]

    mock_repo = MagicMock()
    mock_repo.get_by_id = AsyncMock(return_value={"id": "emb-100", "vector": job_vec})

    scorer = SemanticScorer(
        candidate_vector=candidate_vec,
        embedding_repo=mock_repo,
    )

    score = await scorer.score_async("emb-100")
    assert score == 1.0
