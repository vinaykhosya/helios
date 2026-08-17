"""
run.py — Helios v3.0 Mission Control Runner

Launches the unified FastAPI backend, Mission Control UI,
and opens the default browser for instant daily job execution.

Usage:
    python run.py
    python run.py --port 8080 --no-browser
"""
from __future__ import annotations

import os
import sys
import time
import argparse
import webbrowser
import threading
import uvicorn
from dotenv import load_dotenv

# Load local environment variables if present
load_dotenv()

BANNER = r"""
===================================================================
  _    _ ______ _      _____ ____   _____                 ____  
 | |  | |  ____| |    |_   _/ __ \ / ____|               |___ \ 
 | |__| | |__  | |      | || |  | | (___   __   _________  __) |
 |  __  |  __| | |      | || |  | |\___ \  \ \ / /__  / _ \|__ < 
 | |  | | |____| |____ _| || |__| |____) |  \ V /  / / (_) |__) |
 |_|  |_|______|______|_____\____/|_____/    \_/  /___\___/____/ 

  JOB SEARCH OPERATING SYSTEM — MISSION CONTROL & AI ENGINE
===================================================================
"""


def open_browser_delayed(url: str, delay_seconds: float = 1.5):
    """Opens the user's default browser after server initialization."""
    def _target():
        time.sleep(delay_seconds)
        try:
            webbrowser.open(url)
        except Exception as e:
            print(f"[Runner] Notice: Could not open browser automatically: {e}")
    threading.Thread(target=_target, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="Helios v3.0 Mission Control Runner")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload for development")
    parser.add_argument("--no-browser", action="store_true", default=False, help="Do not open browser automatically")

    args = parser.parse_args()

    print(BANNER)
    server_url = f"http://{args.host}:{args.port}"
    print(f"☀️  Helios Mission Control : {server_url}")
    print(f"📄 API Documentation      : {server_url}/docs")
    print(f"⚡ Daily Queue Target     : Vinay Khosya (NSUT Delhi)")
    print(f"📊 Mode                   : Authoritative DB + Push-Only Projections\n")
    print("Starting Helios platform server... Press Ctrl+C to shutdown.\n")

    if not args.no_browser:
        open_browser_delayed(server_url, delay_seconds=1.5)

    uvicorn.run(
        "backend.src.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )


if __name__ == "__main__":
    main()
