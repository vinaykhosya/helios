"""
tests/unit/intelligence/test_dry_run_mode.py

Unit tests for ActionExecutor dry_run mode safety invariant.
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


@pytest.mark.asyncio
async def test_action_executor_dry_run_never_clicks_submit():
    mock_page = AsyncMock()
    mock_page.url = "https://jobs.lever.co/cred/123/apply"
    mock_page.inner_text = AsyncMock(return_value="Application form page")

    mock_submit_elem = AsyncMock()
    mock_submit_elem.is_visible = AsyncMock(return_value=True)

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
    assert plan.submission_allowed is True

    # Execute in dry_run mode
    executor = ActionExecutor(mode="dry_run")
    evidence = await executor.execute_plan(mock_page, plan)

    # In dry_run mode, submit_clicked MUST be False
    assert evidence.submit_clicked is False
    assert evidence.is_strong_evidence() is False
    assert any("[DRY_RUN]" in (rec.error or "") for rec in evidence.actions)
