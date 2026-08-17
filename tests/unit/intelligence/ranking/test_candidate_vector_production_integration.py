"""
tests/unit/intelligence/ranking/test_candidate_vector_production_integration.py

End-to-End Production Integration Test:
CandidateProfile -> generate_candidate_vector (LocalEmbeddingProvider) ->
SemanticScorer -> SQLAlchemyEmbeddingRepository -> RankingAgent -> Dimension 5 Semantic Match
"""
import uuid
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from core.config.profile_loader import load_candidate_profile
from core.events.definitions import JobPersisted, EmbeddingGenerated
from core.models.job import Job, JobSource, RemotePolicy
from database.models.base import Base
from backend.src.repositories.job import SQLAlchemyJobRepository
from backend.src.repositories.embedding import SQLAlchemyEmbeddingRepository
from intelligence.embeddings.provider import LocalEmbeddingProvider
from intelligence.ranking.semantic_scorer import (
    SemanticScorer,
    build_candidate_profile_text,
    generate_candidate_vector,
)
from intelligence.ranking.ranker import RankingAgent
from workers.embedding_worker import EmbeddingWorker
from workers.orchestrator import WorkflowOrchestrator


class RecordingBus:
    def __init__(self):
        self.handlers = {}
        self.published = []

    def subscribe(self, event_type: str, handler):
        self.handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event):
        self.published.append(event)
        # Deliver to subscribers synchronously in test
        for h in self.handlers.get(getattr(event, "type", type(event).__name__), []):
            await h(event)


@pytest.fixture
async def db_session():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        execution_options={"schema_translate_map": {"helios": None}},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_end_to_end_candidate_profile_semantic_ranking_production_path(db_session):
    # 1. Load candidate profile
    profile = load_candidate_profile()
    assert profile.name != ""

    # 2. Build candidate text and generate real 384-d candidate vector via LocalEmbeddingProvider
    profile_text = build_candidate_profile_text(profile)
    assert "FastAPI" in profile_text or "Python" in profile_text or len(profile_text) > 20

    provider = LocalEmbeddingProvider()
    candidate_vec = await generate_candidate_vector(profile, provider)
    assert len(candidate_vec) == 384

    # 3. Setup repositories and SemanticScorer with candidate vector and DB embedding repo
    job_repo = SQLAlchemyJobRepository(db_session)
    embedding_repo = SQLAlchemyEmbeddingRepository(db_session)

    scorer = SemanticScorer(
        candidate_vector=candidate_vec,
        embedding_repo=embedding_repo,
    )

    # 4. Create and persist a high-fit job in DB
    job_id = str(uuid.uuid4())
    job = Job(
        id=job_id,
        source=JobSource.LINKEDIN,
        source_id="job-prod-fastapi-99",
        source_url="https://linkedin.com/jobs/view/99",
        title="Senior Python Backend Developer (FastAPI & Cloud Systems)",
        company="TechCorp Denmark",
        location="Copenhagen",
        remote=RemotePolicy.REMOTE,
        description="We are seeking an experienced Backend Engineer with expertise in Python, FastAPI, Docker, and PostgreSQL.",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker"],
        experience_years=2,
    )
    await job_repo.create(job)
    await db_session.commit()

    # 5. EmbeddingWorker generates and persists job vector to database
    bus = RecordingBus()
    worker = EmbeddingWorker(
        event_bus=bus,
        embedding_provider=provider,
        job_repo=job_repo,
        embedding_repo=embedding_repo,
    )

    event = JobPersisted(
        job_id=job_id,
        source="linkedin",
        source_url="https://linkedin.com/jobs/view/99",
    )
    await worker.handle_job_persisted(event)
    await db_session.commit()

    # Verify EmbeddingGenerated event was emitted with valid embedding_id
    embedding_event = [e for e in bus.published if isinstance(e, EmbeddingGenerated)][0]
    embedding_id = embedding_event.embedding_id
    assert embedding_id != ""

    # 6. Rank job using RankingAgent wired with the production SemanticScorer
    ranker = RankingAgent(profile, semantic_scorer=scorer)

    # Asynchronously score via repo and cache
    semantic_score_async = await scorer.score_async(embedding_id)
    assert semantic_score_async > 0.65  # Clear non-neutral match (substantially above 0.5)

    ranking = ranker.rank(job, embedding_id=embedding_id)

    # 7. Assertions on the 5 Dimensions
    semantic_dim = next(d for d in ranking.dimensions if d.name == "Semantic")
    assert semantic_dim.score == semantic_score_async
    assert semantic_dim.score > 0.65       # REAL semantic score > 0.5 neutral fallback
    assert semantic_dim.weight == 0.15
    assert semantic_dim.matched is True

    assert ranking.overall_score >= 0.75
    assert ranking.confidence >= 0.80

    # 8. Verify missing embedding ID safely degrades to neutral 0.5
    missing_ranking = ranker.rank(job, embedding_id="")
    missing_semantic_dim = next(d for d in missing_ranking.dimensions if d.name == "Semantic")
    assert missing_semantic_dim.score == 0.5
