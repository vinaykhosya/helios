"""
scripts/test_other_workday_tenant.py

Tests Workday navigation strategy on another active Workday tenant (e.g. NVIDIA / Adobe).
Verifies if Workday apply buttons and application forms load when tenant is online.
"""
import sys
import os
import asyncio

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright
from automation.portals.detector import PortalDetector


async def test_nvidia_workday():
    url = "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
    print(f"[TESTING WORKDAY TENANT] Target URL: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        response = await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        portal_id = await PortalDetector.detect(page)
        print(f"  Url:            {page.url}")
        print(f"  Title:          {await page.title()}")
        print(f"  Portal Type:    {portal_id.type.upper()}")
        print(f"  Company Tenant: {portal_id.company.upper()}")

        apply_btn = await page.query_selector("a[data-automation-id='applyButton'], button[data-automation-id='applyButton'], a:has-text('Apply')")
        print(f"  Apply Button Exists: {apply_btn is not None}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_nvidia_workday())
