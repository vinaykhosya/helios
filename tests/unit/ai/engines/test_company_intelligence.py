"""
tests/unit/ai/engines/test_company_intelligence.py

Unit tests for CompanyIntelligenceAgent dossier generation.
"""
import pytest
from ai.engines.company_intelligence import CompanyIntelligenceAgent
from core.models.job import Job, JobSource


@pytest.mark.asyncio
async def test_company_intelligence_agent_generate_dossier():
    agent = CompanyIntelligenceAgent()
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="gh_1",
        source_url="http://ex.com/1",
        title="Senior AI Developer",
        company="Siemens",
        skills=["Python", "PyTorch"],
    )

    dossier = await agent.generate_dossier("Siemens", job)
    assert dossier.company_name == "Siemens"
    assert dossier.target_role == "Senior AI Developer"
    assert len(dossier.likely_interview_questions) >= 3
    assert "Siemens" in dossier.likely_interview_questions[0]
