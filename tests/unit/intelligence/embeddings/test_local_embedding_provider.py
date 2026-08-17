"""
tests/unit/intelligence/embeddings/test_local_embedding_provider.py

Unit tests for LocalEmbeddingProvider and EmbeddingGeneratorStage.
"""
import math
import pytest
from intelligence.embeddings.provider import LocalEmbeddingProvider
from intelligence.pipeline.stages import EmbeddingGeneratorStage
from core.models.job import Job, JobSource


@pytest.mark.asyncio
async def test_local_embedding_provider_dimensionality_and_normalization():
    provider = LocalEmbeddingProvider()
    assert provider.dimensions == 384

    texts = [
        "Senior Backend Engineer with Python, FastAPI, and PostgreSQL expertise.",
        "Frontend Developer specializing in React, TypeScript, and modern CSS.",
    ]
    vectors = await provider.embed(texts)
    assert len(vectors) == 2

    for vec in vectors:
        assert len(vec) == 384
        assert all(isinstance(val, float) and math.isfinite(val) for val in vec)
        # Verify L2 normalization
        norm = math.sqrt(sum(x * x for x in vec))
        assert 0.98 <= norm <= 1.02


@pytest.mark.asyncio
async def test_local_embedding_provider_empty_list():
    provider = LocalEmbeddingProvider()
    vectors = await provider.embed([])
    assert vectors == []


@pytest.mark.asyncio
async def test_embedding_generator_stage_is_noop_stub():
    stage = EmbeddingGeneratorStage()
    jobs = [
        Job(
            id="job-1",
            source=JobSource.LINKEDIN,
            source_id="123",
            source_url="https://linkedin.com/jobs/view/123",
            title="Backend Engineer",
            company="Acme",
            location="Remote",
            apply_url="https://example.com/apply",
        )
    ]
    processed = await stage.process(jobs)
    assert len(processed) == 1
    assert processed[0].id == "job-1"
