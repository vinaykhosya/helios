"""
scripts/export_cookies.py

Playwright Cookie Exporter for Railway / Cloud Deployment.
Launches a Chromium browser on your local machine so you can log into LinkedIn,
Naukri, or Instahyre ONCE, and saves storage_state.json for 24/7 autonomous filler workers.
"""
import sys
import os
import json
from playwright.sync_api import sync_playwright


def export_cookies():
    print("🚀 Launching Playwright Chromium for Cookie Authentication...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        print("1. Opening LinkedIn Login page...")
        page.goto("https://www.linkedin.com/login")
        print("👉 Please log into LinkedIn in the opened browser window.")
        print("Press ENTER here in terminal after you are fully logged in...")
        input()

        state = context.storage_state()
        output_file = "storage_state.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        print(f"✅ Cookies exported successfully to {output_file}!")
        print("To use on Railway / Vercel:")
        print(f"Copy the JSON string inside {output_file} and add as environment variable LINKEDIN_STORAGE_STATE!")
        browser.close()


if __name__ == "__main__":
    export_cookies()
