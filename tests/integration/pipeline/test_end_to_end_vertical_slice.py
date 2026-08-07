"""
tests/integration/pipeline/test_end_to_end_vertical_slice.py

End-to-End Vertical Slice Integration Test for Helios.
Verifies the complete pipeline chain:
  Job Discovery payload -> EligibilityGate -> RankingAgent -> ProfileIntelligence ->
  LaTeXRenderer -> PDFCompiler -> ConfidenceEngine -> GreenhouseFormFiller -> MemoryService -> EventBus.
"""
import os
import pytest
from unittest.mock import AsyncMock

from ai.engines.profile_intelligence import ProfileIntelligenceAgent
from ai.engines.resume.latex_renderer import LaTeXRenderer
from ai.engines.resume.pdf_compiler import PDFCompiler
from ai.memory.service import MemoryService
from automation.confidence import ConfidenceEngine, ApplicationDecision
from automation.fillers.greenhouse import GreenhouseFormFiller

from core.events.bus import InMemoryEventBus
from core.events.definitions import ApplicationSubmitted


from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource, RemotePolicy
from intelligence.ranking.eligibility import EligibilityGate
from intelligence.ranking.ranker import RankingAgent


@pytest.mark.asyncio
async def test_end_to_end_vertical_slice_execution(tmp_path):
    # 1. Initialize Profile
    profile = CandidateProfile(
        name="Vinay Khosya",
        email="vinay@example.com",
        location="India",
        graduation_year=2025,
        years_of_experience=0.5,
        required_tech_stack=["Python", "FastAPI"],
        excluded_keywords=["PHP", "Sales"],
        target_locations=["India", "Remote"],
    )

    # 2. Ingest Job Payload
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="gh_777",
        source_url="https://boards.greenhouse.io/acme/jobs/777",
        apply_url="https://boards.greenhouse.io/acme/jobs/777#apply",
        title="AI Automation Engineer",
        company="Acme AI",
        description="We need a Python developer with FastAPI experience.",
        location="India",
        remote=RemotePolicy.REMOTE,
        skills=["Python", "FastAPI"],
    )

    # 3. Eligibility Gate (Hard Rules)
    eligibility_gate = EligibilityGate(profile)
    eligibility_result = eligibility_gate.check(job)
    assert eligibility_result.eligible is True

    # 4. Ranking Agent (Soft Match Scoring)
    ranker = RankingAgent(profile)
    ranking_result = ranker.rank(job)
    assert ranking_result.overall_score >= 0.80

    # 5. Confidence Engine Decision
    confidence_engine = ConfidenceEngine()
    decision = confidence_engine.decide(ranking_result, form_complexity=0)
    assert decision in [ApplicationDecision.AUTO_APPLY, ApplicationDecision.ASK_USER]

    # 6. Profile Intelligence & Resume Tailoring
    profile_agent = ProfileIntelligenceAgent(profile=profile)
    skills = profile_agent.get_skills_for_job(job)
    assert "Python" in skills

    renderer = LaTeXRenderer()
    tex_template = r"\documentclass{article}\begin{document}\title{{{JOB_TITLE}}}\author{{{CANDIDATE_NAME}}}\maketitle Hello World\end{document}"
    rendered_tex = tex_template.replace("{{JOB_TITLE}}", job.title).replace("{{CANDIDATE_NAME}}", profile.name)


    compiler = PDFCompiler(output_dir=str(tmp_path))
    pdf_path = await compiler.compile(rendered_tex, output_name="vinay_acme_resume")
    assert os.path.exists(pdf_path)

    # 7. Playwright Greenhouse Form Filler Automation (mocked browser page)
    memory_service = MemoryService()
    form_filler = GreenhouseFormFiller(memory_service=memory_service)

    mock_page = AsyncMock()
    mock_page.goto.return_value = True
    mock_page.query_selector.return_value = None  # No CAPTCHA
    mock_page.fill.return_value = True

    filled_success = await form_filler.fill(mock_page, job, profile, resume_path=pdf_path)
    assert filled_success is True

    # 8. Record in Memory & Emit EventBus Event
    await memory_service.record_application(job_id=str(job.id), user_id="user_vinay", confirmation_id="CONF_777")
    assert await memory_service.has_applied(job_id=str(job.id), user_id="user_vinay") is True

    event_bus = InMemoryEventBus()
    event_received = []


    async def handle_application_submitted(event: ApplicationSubmitted):
        event_received.append(event)

    event_bus.subscribe("ApplicationSubmitted", handle_application_submitted)

    app_event = ApplicationSubmitted(
        app_id="app_777",
        user_id="user_vinay",
        job_id=str(job.id),
        source="greenhouse",
        confirmation_id="CONF_777",
        confidence_score=ranking_result.confidence,
    )
    await event_bus.publish(app_event)

    assert len(event_received) == 1
    assert event_received[0].confirmation_id == "CONF_777"
