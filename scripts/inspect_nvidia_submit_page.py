"""
scripts/inspect_nvidia_submit_page.py

Helios v5.0 NVIDIA Final Page Forensic Inspection Script.
Navigates the NVIDIA application flow, captures the complete DOM forensic snapshot
(all buttons, inputs, links, roles, attributes, iframes, and visibility states),
and writes forensic records to:
  data/diagnostics/nvidia_submit_forensics_<timestamp>.json
  data/diagnostics/nvidia_submit_page_<timestamp>.png
"""
import sys
import os
import asyncio
import json
import time

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright
from automation.discovery.destination_resolver import ApplyDestinationResolver
from automation.portals.detector import PortalDetector
from automation.intelligence.submit_detector import SubmitControlDetector
from automation.portals.strategies.generic import GenericStrategy
from automation.fillers.semantic_filler import DEFAULT_CANDIDATE_PROFILE


def safe_print(msg: str):
    print(msg.encode("ascii", errors="ignore").decode("ascii"))


async def inspect_nvidia():
    url = "https://jobs.nvidia.com/careers/job/893392590814"
    safe_print(f"[NVIDIA INSPECTOR] Navigating to NVIDIA job: {url}")

    diagnostics_dir = os.path.join(base_dir, "data", "diagnostics")
    os.makedirs(diagnostics_dir, exist_ok=True)
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Step 1: Navigate to job detail & resolve Apply destination
        res = await ApplyDestinationResolver.resolve_destination(page, url)
        safe_print(f"[NVIDIA] Apply destination resolved: {res.final_url}")

        # Step 2: Upload Resume & Fill Form
        resume_pdf_path = os.path.join(base_dir, "Vinay_Khosya_NVIDIA_v5_Resume.pdf")
        if not os.path.exists(resume_pdf_path):
            with open(resume_pdf_path, "wb") as f:
                f.write(b"%PDF-1.4 Resume Binary Payload")

        strategy = GenericStrategy(company_name="nvidia")
        plan, evidence = await strategy.execute_application(
            page,
            candidate_profile=DEFAULT_CANDIDATE_PROFILE,
            resume_pdf_path=resume_pdf_path
        )

        # Step 3: Run SubmitControlDetector Analysis
        scan_res = await SubmitControlDetector.scan_page(page)

        # Step 4: Extract Complete Forensic DOM Snapshot
        body_text = await page.inner_text("body")
        title = await page.title()
        current_url = page.url

        buttons_info = []
        elements = await page.query_selector_all("button, input[type='submit'], input[type='button'], a[role='button'], [role='button']")
        for el in elements:
            try:
                vis = await el.is_visible()
                txt = (await el.inner_text()).strip()
                val = await el.get_attribute("value") or ""
                tag = await el.evaluate("e => e.tagName.toLowerCase()")
                el_type = await el.get_attribute("type") or ""
                role = await el.get_attribute("role") or ""
                aria_lbl = await el.get_attribute("aria-label") or ""
                aria_lblby = await el.get_attribute("aria-labelledby") or ""
                auto_id = await el.get_attribute("data-automation-id") or ""
                test_id = await el.get_attribute("data-testid") or ""
                data_qa = await el.get_attribute("data-qa") or ""
                dis_attr = await el.get_attribute("disabled") is not None
                aria_dis = await el.get_attribute("aria-disabled") == "true"
                cls = await el.get_attribute("class") or ""
                box = await el.bounding_box()

                buttons_info.append({
                    "tag": tag,
                    "text": txt or val or aria_lbl,
                    "type": el_type,
                    "role": role,
                    "aria_label": aria_lbl,
                    "aria_labelledby": aria_lblby,
                    "data_automation_id": auto_id,
                    "data_testid": test_id,
                    "data_qa": data_qa,
                    "disabled": dis_attr,
                    "aria_disabled": aria_dis,
                    "visible": vis,
                    "classes": cls,
                    "bounding_box": box
                })
            except Exception:
                pass

        iframes_info = []
        for frame in page.frames:
            iframes_info.append({
                "name": frame.name,
                "url": frame.url
            })

        forensic_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "company": "NVIDIA",
            "job_url": url,
            "final_url": current_url,
            "page_title": title,
            "body_text_length": len(body_text),
            "body_text_snippet": body_text[:2000],
            "submit_scan_found": scan_res.found,
            "submit_scan_diagnostic": scan_res.diagnostic_reason,
            "best_candidate": scan_res.best_candidate.__dict__ if scan_res.best_candidate else None,
            "total_interactive_controls_found": len(buttons_info),
            "interactive_controls": buttons_info,
            "iframes": iframes_info
        }

        # Save Artifacts
        json_file = os.path.join(diagnostics_dir, f"nvidia_submit_forensics_{timestamp_str}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(forensic_data, f, indent=2)

        png_file = os.path.join(diagnostics_dir, f"nvidia_submit_page_{timestamp_str}.png")
        await page.screenshot(path=png_file)

        safe_print(f"\n[FORENSIC SNAPSHOT PERSISTED]")
        safe_print(f"JSON Ledger: {json_file}")
        safe_print(f"Screenshot:  {png_file}")
        safe_print(f"Controls Scanned: {len(buttons_info)}")
        safe_print(f"Submit Scan Found: {scan_res.found} (Diagnostic: {scan_res.diagnostic_reason})\n")

        await browser.close()
        return json_file, png_file


if __name__ == "__main__":
    asyncio.run(inspect_nvidia())
