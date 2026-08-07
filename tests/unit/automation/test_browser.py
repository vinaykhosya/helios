"""
tests/unit/automation/test_browser.py

Unit tests for BrowserSession context manager.
"""
import pytest
from automation.browser import BrowserSession


@pytest.mark.asyncio
async def test_browser_session_lifecycle():
    async with BrowserSession(headless=True) as page:
        assert page is not None
        await page.goto("https://example.com")
        assert page.url is not None
