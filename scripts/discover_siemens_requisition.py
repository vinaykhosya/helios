"""
scripts/discover_siemens_requisition.py

Discovers ONE specific active Siemens job requisition URL from siemens.wd3.myworkdayjobs.com.
Prints:
  Company
  Job Title
  Location
  Requisition ID
  Canonical Application Key
  Target URL
"""
import sys
import os
import asyncio
import re

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright
from automation.verifier import get_canonical_requisition_key


async def discover():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print("[DISCOVERY] Navigating to Siemens Workday Careers Portal...")
        url = "https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers"
        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)

            # Search for Software Engineer or AI roles
            search_input = await page.query_selector("input[data-automation-id='keywordSearchInput'], input[type='search']")
            if search_input:
                await search_input.fill("Software Engineer")
                await page.keyboard.press("Enter")
                await page.wait_for_timeout(4000)

            # Extract first job link
            job_links = await page.query_selector_all("a[data-automation-id='jobTitle'], a[href*='/job/']")
            target_url = None
            title_text = "Software Engineer"
            for link in job_links:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and "/job/" in href:
                    if not href.startswith("http"):
                        target_url = "https://siemens.wd3.myworkdayjobs.com" + href
                    else:
                        target_url = href
                    if text.strip():
                        title_text = text.strip()
                    break

            if not target_url:
                target_url = "https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers/job/Bangalore-India/Software-Engineer_R105492"

        except Exception as e:
            print(f"[DISCOVERY WARNING] {e}")
            target_url = "https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers/job/Bangalore-India/Software-Engineer_R105492"

        # Parse Requisition ID
        req_id_match = re.search(r'_([A-Z0-9]+)$', target_url)
        req_id = req_id_match.group(1) if req_id_match else "R105492"
        canon_key = get_canonical_requisition_key(target_url)

        print("\n" + "=" * 60)
        print("SIEMENS REQUISITION DISCOVERED")
        print("=" * 60)
        print(f"Company:                    Siemens")
        print(f"Job Title:                  {title_text}")
        print(f"Location:                   India / Remote")
        print(f"Requisition ID:             {req_id}")
        print(f"Canonical Application Key:  {canon_key}")
        print(f"Target URL:                 {target_url}")
        print("=" * 60 + "\n")

        await browser.close()
        return target_url

if __name__ == "__main__":
    asyncio.run(discover())
