"""
tests/unit/intelligence/test_planner_and_executor.py

Unit tests for ExecutionPlanner and ActionExecutor emitting EvidencePayload.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from automation.intelligence.contracts import (
    PageType,
    ElementSemantic,
    PageSchema,
    DetectedElement
)
from automation.intelligence.planner import ExecutionPlanner
from automation.intelligence.executor import ActionExecutor


def test_planner_creates_submittable_plan():
    fields = [
        DetectedElement("f-1", "input[name='name']", "input", "text", ElementSemantic.FIRST_NAME, 0.99),
        DetectedElement("f-2", "input[name='email']", "input", "text", ElementSemantic.EMAIL, 0.99)
    ]
    buttons = [
        DetectedElement("b-1", "button[type='submit']", "button", "submit", ElementSemantic.SUBMIT_APPLICATION, 0.99)
    ]
    schema = PageSchema(
        page_type=PageType.APPLICATION_FORM,
        ats_type="lever",
        fields=fields,
        buttons=buttons
    )

    planner = ExecutionPlanner()
    plan = planner.create_plan(schema, resume_pdf_path="resume.pdf")

    assert plan.page_type == PageType.APPLICATION_FORM
    assert plan.submission_allowed is True
    assert plan.recovery_required is False
    assert len(plan.actions) == 4  # Name, Email, Resume Attach, Submit Click


@pytest.mark.asyncio
async def test_action_executor_disallowed_submission_does_not_click():
    mock_page = AsyncMock()
    mock_page.url = "https://jobs.lever.co/cred/123/apply"
    mock_page.inner_text = AsyncMock(return_value="Application form page")

    fields = [
        DetectedElement("f-1", "input[name='name']", "input", "text", ElementSemantic.FIRST_NAME, 0.99)
    ]
    buttons = [
        DetectedElement("b-1", "button[type='submit']", "button", "submit", ElementSemantic.SUBMIT_APPLICATION, 0.99)
    ]
    schema = PageSchema(
        page_type=PageType.APPLICATION_FORM,
        ats_type="lever",
        fields=fields,
        buttons=buttons
    )

    planner = ExecutionPlanner()
    plan = planner.create_plan(schema)
    plan.submission_allowed = False  # Manually disallow submission

    executor = ActionExecutor()
    evidence = await executor.execute_plan(mock_page, plan)

    assert evidence.submit_clicked is False
    assert evidence.is_strong_evidence() is False
