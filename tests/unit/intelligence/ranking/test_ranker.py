"""
tests/unit/intelligence/ranking/test_ranker.py

Unit tests for RankingAgent v3.0.
Validates the 5-dimension system, weight integrity, and embedding_id semantics.
"""
import pytest
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource, RemotePolicy
from intelligence.ranking.ranker import RankingAgent


def _make_profile() -> CandidateProfile:
    from core.config.profile_loader import load_candidate_profile
    return load_candidate_profile()


def _make_job(**kwargs) -> Job:
    defaults = dict(
        source=JobSource.GREENHOUSE,
        source_id="test-001",
        source_url="https://boards.greenhouse.io/test/1",
        title="Software Engineer",
        company="Acme Corp",
        description="Python FastAPI backend role",
        skills=["Python", "FastAPI"],
        remote=RemotePolicy.REMOTE,
    )
    defaults.update(kwargs)
    return Job(**defaults)


def test_weights_sum_to_one():
    """Dimension weights must sum to 1.0. Guards against future drift."""
    weights = RankingAgent.DIMENSION_WEIGHTS
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-6, (
        f"RankingAgent.DIMENSION_WEIGHTS must sum to 1.0, got {total}"
    )


def test_rank_returns_five_dimensions():
    """rank() must return exactly 5 dimensions."""
    profile = _make_profile()
    agent = RankingAgent(profile)
    job = _make_job()
    result = agent.rank(job)
    assert len(result.dimensions) == 5
    names = {d.name for d in result.dimensions}
    assert "Tech Stack" in names
    assert "Location" in names
    assert "Seniority" in names
    assert "Role Title" in names
    assert "Semantic" in names


def test_rank_with_empty_embedding_id_returns_semantic_05():
    """
    embedding_id="" -> _compute_semantic_score returns 0.5.
    This is CORRECT Phase 0-6 behaviour, not a bug.
    """
    profile = _make_profile()
    agent = RankingAgent(profile)
    assert agent._compute_semantic_score("") == 0.5


def test_rank_with_real_embedding_id_still_returns_05_in_phase06():
    """
    embedding_id="real-uuid" -> _compute_semantic_score still returns 0.5.
    SemanticScorer not yet injected -- this is correct for Phase 6 scope.
    Phase 7 will wire real cosine similarity.
    """
    profile = _make_profile()
    agent = RankingAgent(profile)
    score = agent._compute_semantic_score("550e8400-e29b-41d4-a716-446655440000")
    assert score == 0.5, (
        "Phase 6: _compute_semantic_score returns 0.5 even with real embedding_id. "
        "Real SemanticScorer is Phase 7."
    )


def test_rank_accepts_embedding_id_kwarg():
    """rank(job, embedding_id=...) must not raise TypeError."""
    profile = _make_profile()
    agent = RankingAgent(profile)
    job = _make_job()
    # Must not raise
    result = agent.rank(job, embedding_id="some-uuid")
    assert result.overall_score >= 0.0
    assert result.overall_score <= 1.0


def test_rank_overall_score_in_bounds():
    """overall_score must be in [0.0, 1.0]."""
    profile = _make_profile()
    agent = RankingAgent(profile)
    job = _make_job()
    result = agent.rank(job)
    assert 0.0 <= result.overall_score <= 1.0
    assert 0.0 <= result.confidence <= 1.0
