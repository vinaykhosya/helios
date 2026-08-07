"""
scripts/export_brave_cookies.py

Automatic Cookie Extractor using your existing Brave Browser session.
Launches Brave Browser with your existing profile, opens LinkedIn (where you are already logged in),
and automatically extracts storage_state.json for Railway / 24/7 automation without needing passwords!
"""
import sys
import os
import json
import time
from playwright.sync_api import sync_playwright

BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
BRAVE_USER_DATA = os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\User Data")


def extract_brave_session():
    print("[+] Connecting to your existing Brave Browser session...")
    
    if not os.path.exists(BRAVE_PATH):
        print(f"[-] Brave executable not found at {BRAVE_PATH}")
        return

    with sync_playwright() as p:
        user_dir = os.path.expanduser(r"~\AppData\Local\BraveSoftware\Brave-Browser\HeliosProfile")
        context = p.chromium.launch_persistent_context(
            user_data_dir=user_dir,
            executable_path=BRAVE_PATH,
            headless=False
        )
        page = context.pages[0] if context.pages else context.new_page()

        print("[+] Opening LinkedIn in Brave...")
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        
        print("[!] If you are not logged in, please log in now in the Brave window.")
        print("[!] Press ENTER in this terminal when you are logged into LinkedIn...")
        input()

        # Grab logged-in session cookies
        state = context.storage_state()
        output_file = "storage_state.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

        print("=" * 60)
        print(f"[+] SUCCESS! Saved logged-in LinkedIn session cookies!")
        print(f"Saved to: {os.path.abspath(output_file)}")
        print("=" * 60)
        print("\nTo use on Railway / Vercel:")
        print("Copy the JSON content from storage_state.json and add environment variable LINKEDIN_STORAGE_STATE on Railway!")
        
        context.close()


if __name__ == "__main__":
    extract_brave_session()
