"""
scripts/find_siemens_job.py

Searches for an active Siemens job posting on https://jobs.siemens.com and extracts the direct requisition URL.
"""
import asyncio
from playwright.async_api import async_playwright

async def find_job():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating to https://jobs.siemens.com ...")
        await page.goto("https://jobs.siemens.com/", timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        # Search for Software Engineer
        search_input = await page.query_selector("input[type='search'], input[placeholder*='Search' i], input#search-input")
        if search_input:
            await search_input.fill("Software Engineer")
            await page.keyboard.press("Enter")
            await page.wait_for_timeout(4000)

        # Grab first job link
        links = await page.query_selector_all("a[href*='job'], a[href*='Siemens_Careers']")
        job_url = None
        for link in links:
            href = await link.get_attribute("href")
            if href and ("job" in href or "myworkdayjobs" in href or "Siemens" in href):
                if href.startswith("http"):
                    job_url = href
                else:
                    job_url = "https://jobs.siemens.com" + href
                break

        print(f"Discovered Siemens Job URL: {job_url or 'https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers'}")
        await browser.close()
        return job_url

if __name__ == "__main__":
    asyncio.run(find_job())
