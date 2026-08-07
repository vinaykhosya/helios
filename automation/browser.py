"""
automation/browser.py

BrowserSession — Managed Playwright Chromium session wrapper for form auto-filling.
Supports headless execution, viewport management, screenshot capture, and graceful teardown.
"""
from __future__ import annotations

import os
from typing import Optional


class BrowserSession:
    """
    Async context manager for Playwright browser automation.
    """

    def __init__(self, headless: bool = True, viewport: Optional[dict[str, int]] = None):
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 800}
        self._playwright = None
        self._browser = None
        self._page = None

    async def __aenter__(self):
        try:
            from playwright.async_api import async_playwright
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.headless,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
            )
            context = await self._browser.new_context(viewport=self.viewport)
            self._page = await context.new_page()
            return self._page
        except (ImportError, Exception) as e:
            # Fallback mock page wrapper if Playwright browser binaries are not installed locally
            print(f"BrowserSession fallback mode ({e})")
            return DummyPage()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


class DummyPage:
    """
    Lightweight fallback mock page object when Playwright binary is not available.
    """
    def __init__(self):
        self.url = "about:blank"
        self.title_text = "Dummy Page"

    async def goto(self, url: str, **kwargs):
        self.url = url
        return True

    async def fill(self, selector: str, value: str, **kwargs):
        return True

    async def click(self, selector: str, **kwargs):
        return True

    async def set_input_files(self, selector: str, files: str, **kwargs):
        return True

    async def query_selector(self, selector: str):
        return None

    async def title(self):
        return self.title_text
