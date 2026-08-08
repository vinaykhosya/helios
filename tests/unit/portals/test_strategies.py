"""
tests/unit/portals/test_strategies.py

Unit tests for Helios v5.0 ATS Strategies (LeverStrategy, WorkdayStrategy, GenericStrategy).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from automation.portals.strategies.lever import LeverStrategy
from automation.portals.strategies.workday import WorkdayStrategy
from automation.portals.strategies.generic import GenericStrategy


@pytest.mark.asyncio
async def test_lever_strategy_execution():
    mock_page = AsyncMock()
    mock_page.url = "https://jobs.lever.co/cred/7e4d512e/apply"
    mock_page.title = AsyncMock(return_value="CRED - Apply")
    mock_page.inner_text = AsyncMock(return_value="Name, Email and Phone application form.")

    mock_email_elem = AsyncMock()
    mock_email_elem.is_visible = AsyncMock(return_value=True)

    mock_submit_elem = AsyncMock()
    mock_submit_elem.is_visible = AsyncMock(return_value=True)
    mock_submit_elem.scroll_into_view_if_needed = AsyncMock()
    mock_submit_elem.click = AsyncMock()

    async def fake_query(sel):
        if "autocomplete='email'" in sel or "name='email'" in sel:
            return mock_email_elem
        if "button[type='submit']" in sel:
            return mock_submit_elem
        return None

    mock_page.query_selector = AsyncMock(side_effect=fake_query)

    strategy = LeverStrategy(company_name="cred")
    strategy.executor.mode = "live"  # Set live mode for submit click testing
    plan, evidence = await strategy.execute_application(mock_page)

    assert plan.page_type.value == "APPLICATION_FORM"


@pytest.mark.asyncio
async def test_workday_strategy_execution():
    mock_page = AsyncMock()
    mock_page.url = "https://siemens.wd3.myworkdayjobs.com/Siemens_Careers"
    mock_page.title = AsyncMock(return_value="Siemens Careers - Apply")
    mock_page.inner_text = AsyncMock(return_value="Workday Given Name, Family Name and Email.")

    mock_email_elem = AsyncMock()
    mock_email_elem.is_visible = AsyncMock(return_value=True)

    mock_submit_elem = AsyncMock()
    mock_submit_elem.is_visible = AsyncMock(return_value=True)
    mock_submit_elem.scroll_into_view_if_needed = AsyncMock()
    mock_submit_elem.click = AsyncMock()

    async def fake_query(sel):
        if "autocomplete='email'" in sel or "data-automation-id" in sel:
            return mock_email_elem
        if "button[type='submit']" in sel:
            return mock_submit_elem
        return None

    mock_page.query_selector = AsyncMock(side_effect=fake_query)

    strategy = WorkdayStrategy(company_name="siemens")
    strategy.executor.mode = "live"
    plan, evidence = await strategy.execute_application(mock_page)

    assert plan.page_type.value == "APPLICATION_FORM"


@pytest.mark.asyncio
async def test_generic_strategy_unknown_portal():
    mock_page = AsyncMock()
    mock_page.url = "https://customcareers.com/job/101"
    mock_page.title = AsyncMock(return_value="Apply to Custom Company")
    mock_page.inner_text = AsyncMock(return_value="Fill your details below.")

    mock_page.query_selector = AsyncMock(return_value=None)

    strategy = GenericStrategy(company_name="customcompany")
    plan, evidence = await strategy.execute_application(mock_page)

    assert plan.page_type.value == "APPLICATION_FORM"
    assert plan.submission_allowed is False
    assert plan.recovery_required is True
    assert evidence.submit_clicked is False
