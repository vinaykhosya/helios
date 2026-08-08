"""
tests/unit/intelligence/test_page_understanding.py

Unit tests for PageUnderstandingEngine emitting PageSchema contracts.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from automation.intelligence.contracts import PageType, ElementSemantic
from automation.intelligence.page_understanding import PageUnderstandingEngine


@pytest.mark.asyncio
async def test_page_understanding_application_form():
    mock_page = AsyncMock()
    mock_page.url = "https://jobs.lever.co/cred/123/apply"
    mock_page.title = AsyncMock(return_value="CRED - Apply for Position")
    mock_page.inner_text = AsyncMock(return_value="Please enter your name, email and phone to apply.")

    # Mock query selector to simulate email and submit button found
    mock_email_elem = MagicMock()
    mock_email_elem.is_visible = AsyncMock(return_value=True)

    mock_submit_elem = MagicMock()
    mock_submit_elem.is_visible = AsyncMock(return_value=True)

    async def fake_query(sel):
        if "autocomplete='email'" in sel or "name='email'" in sel:
            return mock_email_elem
        if "button[type='submit']" in sel:
            return mock_submit_elem
        return None

    mock_page.query_selector = AsyncMock(side_effect=fake_query)

    engine = PageUnderstandingEngine()
    schema = await engine.analyze_page(mock_page, ats_type="lever")

    assert schema.page_type == PageType.APPLICATION_FORM
    assert schema.ats_type == "lever"
    assert len(schema.fields) >= 1
    assert schema.fields[0].semantic == ElementSemantic.EMAIL
    assert len(schema.buttons) == 1
    assert schema.buttons[0].semantic == ElementSemantic.SUBMIT_APPLICATION


@pytest.mark.asyncio
async def test_page_understanding_captcha_detection():
    mock_page = AsyncMock()
    mock_page.url = "https://jobs.lever.co/cred/123/apply"
    mock_page.title = AsyncMock(return_value="Security Check Required")
    mock_page.inner_text = AsyncMock(return_value="Attention Required! Cloudflare CAPTCHA challenge.")

    engine = PageUnderstandingEngine()
    schema = await engine.analyze_page(mock_page, ats_type="lever")

    assert schema.page_type == PageType.CAPTCHA_CHALLENGE
    assert schema.has_captcha is True
