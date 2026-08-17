"""
backend/src/api/jobs.py

FastAPI route handlers for Job operations & Jobs Command Center.
Supports rich multi-filtering (Saved Views, Eligibility, Seniority Mismatch, Location),
duplicate grouping, and quick actions (Mark Applied, Skip, Details).
"""
from __future__ import annotations

import os
import csv
import json
import uuid
import httpx
from typing import AsyncGenerator, Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.models.job import Job, RemotePolicy
from core.interfaces.repository import JobRepository, CompanyRepository
from backend.src.core.di import DIContainer
from backend.src.services.job_service import JobService
from automation.connectors.dynamic_crawler import fetch_dynamic_company_jobs, MASTER_EMPLOYER_DIRECTORY
from backend.src.services.profile_service import profile_service

router = APIRouter(prefix="/api/v1/jobs", tags=["Jobs"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CSV_MASTER_PATH = os.path.join(BASE_DIR, "data", "helios_live_jobs.csv")

# Global in-memory cache for fast serverless responses and filtering
IN_MEMORY_JOBS: List[Dict[str, Any]] = []


def _load_master_jobs_dataset() -> List[Dict[str, Any]]:
    """
    Loads and normalizes the live discovered dataset with duplicate grouping,
    5-dimension weighted breakdown, and seniority mismatch classification.
    """
    records: List[Dict[str, Any]] = []
    seen_keys: Dict[str, Dict[str, Any]] = {}

    active_profile = profile_service.get_active_profile()

    if os.path.exists(CSV_MASTER_PATH):
        try:
            with open(CSV_MASTER_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for idx, row in enumerate(reader):
                    company = row.get("Company", "Unknown")
                    title = row.get("Role / Title", "Software Engineer")
                    loc = row.get("Location / Remote", "Remote")
                    exp = row.get("Experience Level", "1-3 yrs")
                    job_type = row.get("Job Type", "Full-Time")
                    comp = row.get("Salary / CTC / Stipend", "Competitive")
                    fit_str = row.get("Match Fit", "85%")
                    fit_score = float(fit_str.replace("%", "")) / 100.0 if "%" in fit_str else 0.85
                    apply_url = row.get("Apply Link", "#")

                    # Deduplication key: normalized company + title + location
                    dup_key = f"{company.lower().strip()}_{title.lower().strip()}_{loc.lower().strip()}"

                    # Check for Seniority Mismatch (e.g. 5+ yrs or Manager/Principal for junior profile)
                    is_senior = False
                    if any(k in exp.lower() for k in ["5+", "7+", "5-", "7-", "10+"]):
                        is_senior = True
                    if any(k in title.lower() for k in ["principal", "engineering manager", "director", "head of", "lead architect"]):
                        is_senior = True

                    eligibility_status = "SENIORITY_MISMATCH" if is_senior else "ELIGIBLE"
                    eligibility_reasons = [f"Required experience ({exp}) exceeds profile (max {active_profile.max_experience_years} yrs)"] if is_senior else ["Meets all profile constraints"]

                    is_india = any(k in loc.lower() for k in ["india", "delhi", "gurgaon", "gurugram", "noida", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai"])
                    
                    # 5-Dimension breakdown
                    tech_score = round(min(fit_score * 1.05, 1.0), 2)
                    loc_score = 1.0 if is_india or "remote" in loc.lower() else 0.4
                    sen_score = 0.3 if is_senior else 1.0
                    role_score = 1.0 if any(r.lower() in title.lower() for r in active_profile.ideal_role_keywords) else 0.6
                    sem_score = round(fit_score, 2)

                    breakdown = {
                        "tech_stack": tech_score,
                        "location": loc_score,
                        "seniority": sen_score,
                        "role": role_score,
                        "semantic": sem_score,
                    }

                    if dup_key in seen_keys:
                        # Increment source count on existing grouped job
                        seen_keys[dup_key]["source_count"] += 1
                        seen_keys[dup_key]["other_urls"].append(apply_url)
                        continue

                    job_dict = {
                        "id": f"job-{uuid.uuid5(uuid.NAMESPACE_DNS, f'{company}_{title}_{idx}').hex[:10]}",
                        "company": company,
                        "title": title,
                        "location": loc,
                        "is_india": is_india,
                        "experience_years": exp,
                        "job_type": job_type,
                        "compensation": comp,
                        "fit_score": fit_score,
                        "match_fit": fit_str,
                        "apply_url": apply_url,
                        "source": "Lever / Greenhouse / Ashby" if not is_india else "LinkedIn / Direct Board",
                        "eligibility_status": eligibility_status,
                        "eligibility_reasons": eligibility_reasons,
                        "dimension_breakdown": breakdown,
                        "friction_level": "LOW" if not is_senior else "MODERATE",
                        "application_status": "NOT_APPLIED",
                        "duplicate_group_id": dup_key,
                        "source_count": 1,
                        "other_urls": [apply_url],
                    }

                    seen_keys[dup_key] = job_dict
                    records.append(job_dict)
        except Exception as e:
            print(f"[JobsAPI] Dataset loading notice: {e}")

    if not records:
        raw = fetch_dynamic_company_jobs()
        for idx, r in enumerate(raw):
            r["id"] = r.get("id", f"job-{idx}")
            r["eligibility_status"] = r.get("eligibility_status", "ELIGIBLE")
            r["dimension_breakdown"] = r.get("dimension_breakdown", {"tech_stack": 0.9, "location": 1.0, "seniority": 1.0, "role": 0.9, "semantic": 0.9})
            records.append(r)

    return records


# Initialize dataset
IN_MEMORY_JOBS = _load_master_jobs_dataset()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with DIContainer.session() as session:
        yield session


def get_job_service(session: AsyncSession = Depends(get_db_session)) -> JobService:
    job_repo = DIContainer.resolve_repository(JobRepository, session)
    company_repo = DIContainer.resolve_repository(CompanyRepository, session)
    return JobService(job_repo, company_repo)


@router.get("", response_model=List[dict])
async def list_jobs(
    search: Optional[str] = Query(default=None),
    min_match: Optional[int] = Query(default=None),
    eligibility: Optional[str] = Query(default="all"),  # all | eligible_only | seniority_mismatch
    location: Optional[str] = Query(default="all"),     # all | india | remote
    application_status: Optional[str] = Query(default="all"), # all | not_applied | applied | skipped
) -> List[dict]:
    """Lists filtered jobs from the authoritative store."""
    global IN_MEMORY_JOBS
    if not IN_MEMORY_JOBS:
        IN_MEMORY_JOBS = _load_master_jobs_dataset()

    results = list(IN_MEMORY_JOBS)

    if search:
        s_lower = search.lower()
        results = [
            j for j in results
            if s_lower in j.get("title", "").lower()
            or s_lower in j.get("company", "").lower()
            or s_lower in j.get("location", "").lower()
        ]

    if min_match is not None:
        threshold = float(min_match) / 100.0
        results = [j for j in results if (j.get("fit_score") or 0.0) >= threshold]

    if eligibility == "eligible_only":
        results = [j for j in results if j.get("eligibility_status") == "ELIGIBLE"]
    elif eligibility == "seniority_mismatch":
        results = [j for j in results if j.get("eligibility_status") == "SENIORITY_MISMATCH"]

    if location == "india":
        results = [j for j in results if j.get("is_india", False)]
    elif location == "remote":
        results = [j for j in results if not j.get("is_india", False)]

    if application_status != "all":
        results = [j for j in results if j.get("application_status", "NOT_APPLIED").lower() == application_status.lower()]

    return results


@router.get("/{job_id}")
async def get_job_details(job_id: str) -> dict:
    """Returns granular details, 5-dimension weighted breakdown, and reasons for a specific job."""
    global IN_MEMORY_JOBS
    for j in IN_MEMORY_JOBS:
        if j.get("id") == job_id:
            return j
    raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")


@router.post("/{job_id}/skip")
async def skip_job(job_id: str) -> dict:
    """Marks a job as SKIPPED so it does not clutter the active opportunity pool."""
    global IN_MEMORY_JOBS
    for j in IN_MEMORY_JOBS:
        if j.get("id") == job_id:
            j["application_status"] = "SKIPPED"
            return {"status": "success", "job_id": job_id, "application_status": "SKIPPED"}
    raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")


@router.post("/{job_id}/mark-applied")
async def mark_job_applied_api(job_id: str) -> dict:
    """Marks a job as APPLIED and increments tracking state."""
    global IN_MEMORY_JOBS
    for j in IN_MEMORY_JOBS:
        if j.get("id") == job_id:
            j["application_status"] = "APPLIED"
            return {"status": "success", "job_id": job_id, "application_status": "APPLIED"}
    raise HTTPException(status_code=404, detail=f"Job ID '{job_id}' not found.")
