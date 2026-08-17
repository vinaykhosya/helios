"""
tests/unit/intelligence/ranking/test_ranker_semantic.py

Tests for RankingAgent integration with SemanticScorer.
"""
import pytest
from core.models.job import Job, JobSource, RemotePolicy
from core.models.candidate_profile import CandidateProfile
from intelligence.ranking.ranker import RankingAgent
from intelligence.ranking.semantic_scorer import SemanticScorer


from core.config.profile_loader import load_candidate_profile


@pytest.fixture
def profile():
    return load_candidate_profile()


def test_ranking_agent_with_semantic_scorer(profile):
    candidate_vec = [1.0, 0.0, 0.0]
    job_vec = [1.0, 0.0, 0.0]  # Perfect semantic match -> 1.0

    scorer = SemanticScorer(
        candidate_vector=candidate_vec,
        preloaded_embeddings={"emb-perfect": job_vec},
    )

    ranker = RankingAgent(profile, semantic_scorer=scorer)

    job = Job(
        id="job-rank-1",
        source=JobSource.LINKEDIN,
        source_id="link-1",
        source_url="https://linkedin.com/jobs/1",
        title="Senior Backend Software Engineer",
        company="Acme Corp",
        location="Copenhagen",
        remote=RemotePolicy.REMOTE,
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years=4,
    )

    result = ranker.rank(job, embedding_id="emb-perfect")

    # Find Semantic dimension
    semantic_dim = next(d for d in result.dimensions if d.name == "Semantic")
    assert semantic_dim.score == 1.0
    assert semantic_dim.weight == 0.15
    assert semantic_dim.matched is True

    # Check overall score reflects Dimension 5 (0.15) contribution
    assert result.overall_score >= 0.80
    assert result.confidence >= 0.85


def test_ranking_agent_fallback_when_embedding_empty(profile):
    candidate_vec = [1.0, 0.0, 0.0]
    scorer = SemanticScorer(candidate_vector=candidate_vec)
    ranker = RankingAgent(profile, semantic_scorer=scorer)

    job = Job(
        id="job-rank-2",
        source=JobSource.LINKEDIN,
        source_id="link-2",
        source_url="https://linkedin.com/jobs/2",
        title="Software Engineer",
        company="Acme",
        location="Remote",
    )

    result = ranker.rank(job, embedding_id="")
    semantic_dim = next(d for d in result.dimensions if d.name == "Semantic")
    assert semantic_dim.score == 0.5   # Neutral fallback
