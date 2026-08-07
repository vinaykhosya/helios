"""
tests/unit/intelligence/pipeline/test_stages.py

Unit tests for ingestion pipeline stage contracts.

Phase 1: Verifies that every stage is a contract (raises NotImplementedError).
Phase 3+: Replace or extend these tests with actual stage implementation tests.

Convention for future stage tests:
  - Each stage test creates a list of synthetic Job objects
  - Passes them through the stage
  - Asserts on the output list (length, field values, dropped records)
  - Never hits a real database or network
  - Uses pytest fixtures from tests/conftest.py and tests/fixtures/
"""
import pytest
import asyncio
from intelligence.pipeline.stages import (
    NormalizerStage,
    DeduplicatorStage,
    CompanyResolverStage,
    EmbeddingGeneratorStage,
    RankerStage,
    PersistenceStage,
    INGESTION_PIPELINE,
)


class TestPipelineContracts:
    """Verifies that Phase 1 stages are contracts only — no premature implementations."""

    @pytest.mark.parametrize("StageClass", [s for s in INGESTION_PIPELINE if s not in (PersistenceStage, CompanyResolverStage, DeduplicatorStage, NormalizerStage)])
    @pytest.mark.asyncio
    async def test_stage_raises_not_implemented(self, StageClass):
        stage = StageClass()
        with pytest.raises(NotImplementedError):
            await stage.process([])

    def test_pipeline_order(self):
        """Pipeline stage order is architecture — verify it matches the ADR."""
        expected_names = [
            "normalizer",
            "deduplicator",
            "company_resolver",
            "embedding_generator",
            "ranker",
            "persistence",
        ]
        actual_names = [s.name for s in INGESTION_PIPELINE]
        assert actual_names == expected_names, (
            f"Pipeline order changed! Expected {expected_names}, got {actual_names}. "
            "Update ADR-006 if this change is intentional."
        )

    def test_all_stages_have_name(self):
        class MockRepo:
            pass
        for StageClass in INGESTION_PIPELINE:
            if StageClass == PersistenceStage:
                stage = StageClass(job_repo=MockRepo())
            elif StageClass == DeduplicatorStage:
                stage = StageClass(job_repo=MockRepo())
            elif StageClass == CompanyResolverStage:
                stage = StageClass(company_repo=MockRepo())
            else:
                stage = StageClass()
            assert isinstance(stage.name, str) and stage.name, (
                f"{StageClass.__name__} must define a non-empty name"
            )


# ── DeduplicatorStage & CompanyResolverStage tests ───────────────────────────

class TestDeduplicatorStage:
    @pytest.mark.asyncio
    async def test_passes_unique_job(self, minimal_job):
        class MockJobRepo:
            async def get_by_source_id(self, source, source_id):
                return None  # unique, not found

        stage = DeduplicatorStage(job_repo=MockJobRepo())
        res = await stage.process([minimal_job])
        assert len(res) == 1
        assert res[0].id == minimal_job.id

    @pytest.mark.asyncio
    async def test_drops_duplicate_job(self, minimal_job):
        class MockJobRepo:
            async def get_by_source_id(self, source, source_id):
                return minimal_job  # duplicate found

        stage = DeduplicatorStage(job_repo=MockJobRepo())
        res = await stage.process([minimal_job])
        assert len(res) == 0


class TestCompanyResolverStage:
    @pytest.mark.asyncio
    async def test_resolves_existing_company(self, minimal_job):
        class MockCompanyRepo:
            async def get_by_normalized_name(self, name):
                from core.models.company import Company
                return Company(id="c1", name="Acme A/S")

        stage = CompanyResolverStage(company_repo=MockCompanyRepo())
        res = await stage.process([minimal_job])
        assert len(res) == 1
        assert res[0].company_id == "c1"

    @pytest.mark.asyncio
    async def test_creates_missing_company(self, minimal_job):
        created_companies = []

        class MockCompanyRepo:
            async def get_by_normalized_name(self, name):
                return None

            async def create(self, company):
                created_companies.append(company)
                return company

        stage = CompanyResolverStage(company_repo=MockCompanyRepo())
        res = await stage.process([minimal_job])
        assert len(res) == 1
        assert res[0].company_id is not None
        assert len(created_companies) == 1
        assert created_companies[0].name == minimal_job.company


class TestNormalizerStage:
    @pytest.mark.asyncio
    async def test_strips_html_from_description(self, minimal_job):
        dirty = minimal_job.model_copy(update={"description": "<p>Hello <b>World</b></p>"})
        stage = NormalizerStage()
        result = await stage.process([dirty])
        assert len(result) == 1
        assert result[0].description == "Hello World"

    @pytest.mark.asyncio
    async def test_drops_job_with_empty_title(self, minimal_job):
        bad = minimal_job.model_copy(update={"title": ""})
        stage = NormalizerStage()
        result = await stage.process([bad])
        assert len(result) == 0

