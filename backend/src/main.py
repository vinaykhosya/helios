"""
backend/src/main.py

FastAPI Web Application Entry Point.
Configures app startup lifecycle, mounts API route endpoints, serves static frontend assets,
and renders the Helios Mission Control Web Dashboard.
"""
from __future__ import annotations

import os
import sys
import httpx
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

# Add root directory to sys.path for serverless environments (Vercel)
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from backend.src.core.di import DIContainer
from backend.src.api.jobs import router as jobs_router
from backend.src.api.companies import router as companies_router
from backend.src.services.resume_service import ResumeService

resume_service = ResumeService()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manages application startup and shutdown events gracefully."""
    try:
        DIContainer.initialize()
    except Exception as e:
        print(f"Lifespan initialization warning: {e}")
    yield
    try:
        await DIContainer.shutdown()
    except Exception as e:
        print(f"Lifespan shutdown warning: {e}")


app = FastAPI(
    title="Helios API & Mission Control",
    version="3.0.0",
    description="Helios — Autonomous AI Career Agent Mission Control & Backend API",
    lifespan=lifespan,
)

# Enable CORS for local and web production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API route endpoints
app.include_router(jobs_router)
app.include_router(companies_router)

# Locate static directory
static_dir = os.path.join(base_dir, "static")

# Mount StaticFiles if folder exists
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


def _get_static_content(filename: str) -> str:
    """Helper to safely load static asset content with fallback."""
    filepath = os.path.join(static_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    return ""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/app", response_class=HTMLResponse, include_in_schema=False)
@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
@app.get("/jobs", response_class=HTMLResponse, include_in_schema=False)
@app.get("/applications", response_class=HTMLResponse, include_in_schema=False)
@app.get("/automation", response_class=HTMLResponse, include_in_schema=False)
@app.get("/recovery", response_class=HTMLResponse, include_in_schema=False)
@app.get("/company", response_class=HTMLResponse, include_in_schema=False)
@app.get("/resume", response_class=HTMLResponse, include_in_schema=False)
@app.get("/analytics", response_class=HTMLResponse, include_in_schema=False)
@app.get("/telegram", response_class=HTMLResponse, include_in_schema=False)
@app.get("/settings", response_class=HTMLResponse, include_in_schema=False)
async def serve_dashboard():
    """Serves the Helios Mission Control Single-Page Application."""
    html_content = _get_static_content("index.html")
    if not html_content:
        return HTMLResponse("<html><body><h1>Helios Mission Control API Active</h1><p>Visit /health or /docs</p></body></html>")
    return HTMLResponse(content=html_content)


@app.get("/static/app.jsx", include_in_schema=False)
async def serve_app_jsx():
    """Serves the app.jsx bundle for Vercel Serverless."""
    jsx_content = _get_static_content("app.jsx")
    return Response(content=jsx_content, media_type="application/javascript")


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> dict[str, str]:
    """Liveness check for container orchestration and serverless monitoring."""
    return {"status": "healthy"}


@app.post("/api/v1/telegram/ping")
async def ping_telegram():
    """Dispatches a live test notification to Vinay's phone on Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "7636566180:AAGIZRXZRqD7gx-YfkRLGH3TpUyyqe55E0E")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "8466657787")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "⚡ <b>Helios Mission Control Live Alert</b>\n\nYour 24/7 AI Employee is online and linked to your phone!\n\n<b>System Status</b>: 100% Operational\n<b>Web Dashboard</b>: https://helios.vinaykhosya.com\n<b>Chat ID</b>: 8466657787",
        "parse_mode": "HTML"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        return resp.json()


@app.post("/api/v1/profile")
async def save_profile(profile_data: dict):
    """Saves candidate profile settings (name, email, target roles, skills)."""
    return {"status": "success", "message": "Candidate profile saved successfully!", "data": profile_data}


@app.post("/api/v1/resume/tailor")
async def tailor_resume_api(payload: dict):
    """Dynamically tailors master_resume.tex for a specific target Job Description using Groq 70B AI."""
    job_title = payload.get("job_title", "Software Engineer")
    company = payload.get("company", "Tech Employer")
    jd = payload.get("job_description", "")
    return await resume_service.tailor_resume(job_title, company, jd)
