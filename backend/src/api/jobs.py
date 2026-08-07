"""
backend/src/api/jobs.py

FastAPI route handlers for Job operations.
Exposes CRUD endpoints and Broad Pan-India & Remote Job Discovery Scanner
dynamically crawling 100+ company career pages (Samsung, LG, Nokia, Google, Microsoft, Sarvam AI, Razorpay, etc.)
and Indian Portals (Indeed India, Naukri, Instahyre).
"""
from __future__ import annotations

import os
import json
import httpx
import uuid
from typing import AsyncGenerator, Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.job import Job
from core.interfaces.repository import JobRepository, CompanyRepository
from backend.src.core.di import DIContainer
from backend.src.services.job_service import JobService
from backend.src.ai.provider_pool import ai_engine
from automation.connectors.dynamic_crawler import fetch_dynamic_company_jobs, MASTER_EMPLOYER_DIRECTORY

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])

# Global in-memory cache for fast serverless responses
IN_MEMORY_JOBS: List[Dict[str, Any]] = []


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI Dependency for database session lifecycle management."""
    async with DIContainer.session() as session:
        yield session


def get_job_service(session: AsyncSession = Depends(get_db_session)) -> JobService:
    """FastAPI Dependency for resolving JobService with injected repository protocols."""
    job_repo = DIContainer.resolve_repository(JobRepository, session)
    company_repo = DIContainer.resolve_repository(CompanyRepository, session)
    return JobService(job_repo, company_repo)


@router.get("", response_model=List[dict])
async def list_jobs(
    search: Optional[str] = None,
    service: JobService = Depends(get_job_service)
) -> List[dict]:
    """Lists all active Pan-India & Remote tech jobs tailored for Vinay Khosya across 100+ companies."""
    global IN_MEMORY_JOBS
    try:
        jobs = await service.list_jobs()
        if jobs:
            return [j.model_dump(mode="json") if hasattr(j, "model_dump") else j.__dict__ for j in jobs]
    except Exception as e:
        print(f"PostgreSQL fetch fallback: {e}")
    
    if not IN_MEMORY_JOBS:
        IN_MEMORY_JOBS = fetch_dynamic_company_jobs()
    return IN_MEMORY_JOBS


@router.post("/scan")
async def scan_pan_india_jobs():
    """Triggers Dynamic Multi-Company Career Crawler scanning 100+ employers (Samsung, LG, Nokia, Google, Sarvam AI, Razorpay, etc.)."""
    global IN_MEMORY_JOBS
    IN_MEMORY_JOBS = fetch_dynamic_company_jobs()
    
    # Telegram Bot Alert
    bot_token = os.path.getenv("TELEGRAM_BOT_TOKEN", "7636566180:AAGIZRXZRqD7gx-YfkRLGH3TpUyyqe55E0E")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "8466657787")
    
    company_names = [c["name"] for c in MASTER_EMPLOYER_DIRECTORY[:8]]
    alert_text = (
        f"🎯 <b>Helios Dynamic Crawler Alert: Scanned {len(MASTER_EMPLOYER_DIRECTORY)}+ Employers for Vinay Khosya!</b>\n\n"
        f"• <b>Target Companies Crawled</b>: {', '.join(company_names)}, and 20+ more!\n"
        f"• <b>Channels Crawled</b>: Direct Career Boards (Lever, Greenhouse, Workday), Indeed India, Naukri India, Instahyre.\n"
        f"• <b>Live Positions Found</b>: <b>{len(IN_MEMORY_JOBS)} active jobs</b>\n\n"
        f"Apply on Dashboard: https://helios.vinaykhosya.com"
    )
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": alert_text, "parse_mode": "HTML"}
            )
    except Exception as e:
        print(f"Telegram alert warning: {e}")
        
    return {
        "status": "success",
        "jobs_count": len(IN_MEMORY_JOBS),
        "companies_crawled_count": len(MASTER_EMPLOYER_DIRECTORY),
        "sources": ["Direct Company Career Boards", "Lever", "Greenhouse", "Workday", "Indeed India", "Naukri India", "Instahyre India"],
        "target_candidate": "Vinay Khosya (NSUT Delhi)",
        "jobs": IN_MEMORY_JOBS
    }
