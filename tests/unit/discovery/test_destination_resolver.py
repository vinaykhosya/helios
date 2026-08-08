"""
tests/unit/discovery/test_destination_resolver.py

Unit tests for Helios v5.0 ApplyDestinationResolver.
"""
import pytest
from unittest.mock import AsyncMock
from automation.discovery.destination_resolver import ApplyDestinationResolver


@pytest.mark.asyncio
async def test_destination_resolver_apply_button_found():
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.url = "https://jobs.siemens.com/en_US/externaljobs/job/101"
    mock_page.title = AsyncMock(return_value="Software Engineer Siemens")

    mock_apply_btn = AsyncMock()
    mock_apply_btn.is_visible = AsyncMock(return_value=True)
    mock_apply_btn.get_attribute = AsyncMock(return_value=None)
    mock_apply_btn.click = AsyncMock()

    async def fake_query(sel):
        if "applyButton" in sel or "Apply" in sel:
            return mock_apply_btn
        return None

    mock_page.query_selector = AsyncMock(side_effect=fake_query)

    res = await ApplyDestinationResolver.resolve_destination(mock_page, "https://jobs.siemens.com/en_US/externaljobs/job/101")

    assert res.resolved is True
    assert res.apply_control_found is True
    assert res.is_valid_application_flow is True
    assert len(res.redirect_chain) >= 1


@pytest.mark.asyncio
async def test_destination_resolver_maintenance_redirect():
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.url = "https://community.workday.com/maintenance-page?d=3&s=1&e=1&o="
    mock_page.title = AsyncMock(return_value="Workday is currently unavailable.")

    res = await ApplyDestinationResolver.resolve_destination(mock_page, "https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers/job/101")

    assert res.resolved is False
    assert res.is_maintenance is True
    assert res.error_reason == "WORKDAY_MAINTENANCE_REDIRECT"
