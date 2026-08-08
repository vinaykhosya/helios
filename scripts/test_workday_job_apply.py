"""
scripts/test_workday_job_apply.py

Finds a specific job on NVIDIA Workday portal and tests clicking Apply -> Apply Manually -> Form schema mapping.
"""
import sys
import os
import asyncio

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright
from automation.portals.detector import PortalDetector
from automation.portals.strategies.workday import WorkdayStrategy
from automation.fillers.semantic_filler import DEFAULT_CANDIDATE_PROFILE


async def test_job_apply():
    url = "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite"
    print(f"[WORKDAY WIZARD TEST] Navigating to NVIDIA Workday: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        await page.goto(url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Click first job link
        job_link = await page.query_selector("a[data-automation-id='jobTitle'], a[href*='/job/']")
        if job_link:
            job_title = await job_link.inner_text()
            job_href = await job_link.get_attribute("href")
            print(f"  Discovered Job: '{job_title.strip()}' -> {job_href}")
            await job_link.click()
            await page.wait_for_timeout(4000)

        print(f"  Current URL:   {page.url}")
        print(f"  Current Title: {await page.title()}")

        # Test WorkdayStrategy preparation & field mapping
        strategy = WorkdayStrategy(company_name="nvidia")
        strategy.executor.mode = "dry_run"

        resume_pdf_path = os.path.join(base_dir, "Vinay_Khosya_NVIDIA_v5_Resume.pdf")
        with open(resume_pdf_path, "w", encoding="utf-8") as f:
            f.write("% PDF Binary\n")

        plan, evidence = await strategy.execute_application(
            page,
            candidate_profile=DEFAULT_CANDIDATE_PROFILE,
            resume_pdf_path=resume_pdf_path
        )

        print("\n" + "=" * 60)
        print("WORKDAY WIZARD PLAN & EVIDENCE RESULT")
        print("=" * 60)
        print(f"Page Type:            {plan.page_type.value}")
        print(f"Total Planned Actions: {len(plan.actions)}")
        print(f"Submission Allowed:   {plan.submission_allowed}")
        print(f"Submit Clicked:       {evidence.submit_clicked}")
        print(f"Recovery Required:    {plan.recovery_required}")
        print("=" * 60 + "\n")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_job_apply())
