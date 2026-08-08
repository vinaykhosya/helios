"""
scripts/diagnose_workday_navigation.py

Diagnoses Workday navigation & session redirect steps on live Siemens Workday portal.
Traces:
  - Initial URL & Page Title
  - Presence of Apply buttons
  - Redirect chains
  - Screenshots at each transition
"""
import sys
import os
import asyncio

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright


async def diagnose():
    target_url = "https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers/job/Bangalore-India/Software-Engineer_R105492"
    print(f"[DIAGNOSTIC START] Target URL: {target_url}\n")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Step 1: Initial Navigation
        print("Step 1: Navigating to initial requisition URL...")
        response = await page.goto(target_url, timeout=25000, wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)

        url_step1 = page.url
        title_step1 = await page.title()
        status_step1 = response.status if response else "Unknown"
        heading_elem = await page.query_selector("h1, h2, [data-automation-id='jobPostingHeader']")
        heading_text = (await heading_elem.inner_text()).strip() if heading_elem else "None"

        print(f"  Url:              {url_step1}")
        print(f"  Status Code:      {status_step1}")
        print(f"  Page Title:       {title_step1}")
        print(f"  Visible Heading:  {heading_text}")
        await page.screenshot(path="workday_diag_step1.png")
        print("  Screenshot saved: workday_diag_step1.png\n")

        # Step 2: Apply Button Discovery
        print("Step 2: Searching for Apply buttons in DOM...")
        apply_btn = await page.query_selector("a[data-automation-id='applyButton'], button[data-automation-id='applyButton'], a:has-text('Apply')")
        apply_exists = apply_btn is not None
        apply_visible = await apply_btn.is_visible() if apply_btn else False

        print(f"  Apply Button Exists:   {apply_exists}")
        print(f"  Apply Button Visible:  {apply_visible}")

        if apply_btn and apply_visible:
            print("Step 3: Attempting Click on Apply button...")
            await apply_btn.scroll_into_view_if_needed()
            await apply_btn.click()
            await page.wait_for_timeout(4000)

            url_step3 = page.url
            title_step3 = await page.title()
            print(f"  Url after Apply Click: {url_step3}")
            print(f"  Title after Click:     {title_step3}")
            await page.screenshot(path="workday_diag_step3.png")
            print("  Screenshot saved: workday_diag_step3.png\n")

            # Check for choice dialog (Apply Manually vs Autofill)
            manual_btn = await page.query_selector("button[data-automation-id='applyManually'], a[data-automation-id='applyManually'], button:has-text('Apply Manually')")
            manual_exists = manual_btn is not None
            manual_visible = await manual_btn.is_visible() if manual_btn else False
            print(f"  Apply Manually Choice Button Exists:  {manual_exists}")
            print(f"  Apply Manually Choice Button Visible: {manual_visible}")

            if manual_btn and manual_visible:
                print("Step 4: Attempting Click on Apply Manually...")
                await manual_btn.click()
                await page.wait_for_timeout(4000)
                url_step4 = page.url
                title_step4 = await page.title()
                print(f"  Url after Apply Manually: {url_step4}")
                print(f"  Title after Apply Manually: {title_step4}")
                await page.screenshot(path="workday_diag_step4.png")
                print("  Screenshot saved: workday_diag_step4.png\n")

        await browser.close()
        print("=" * 60)
        print("[DIAGNOSTIC COMPLETE]")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(diagnose())
