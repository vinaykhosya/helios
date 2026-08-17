"""
backend/src/api/tailor.py

FastAPI route handlers for Asynchronous Fact-Constrained AI Resume & Cover Letter Tailoring.
Includes Guard-AGAIN revalidation endpoints and invariant enforcement.
"""
from __future__ import annotations

import os
from typing import Optional, List
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.models.tailor import TailorJob, TailorJobStatus
from backend.src.services.resume_service import resume_service

router = APIRouter(prefix="/api/v1/ai/tailor", tags=["AI Tailoring"])


class TailorRequest(BaseModel):
    job_id: str
    job_title: str
    company_name: str
    job_description: Optional[str] = ""
    required_skills: Optional[List[str]] = None
    profile_id: Optional[str] = "ai_ml"


class RevalidateRequest(BaseModel):
    edited_latex: str


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_tailor_job(payload: TailorRequest, background_tasks: BackgroundTasks) -> dict:
    """Initiates an asynchronous tailoring job with fact verification and returns a persistent tailor_job_id."""
    t_job = resume_service.create_tailor_job(
        job_id=payload.job_id,
        job_title=payload.job_title,
        company_name=payload.company_name,
        profile_id=payload.profile_id or "ai_ml",
    )
    
    background_tasks.add_task(
        resume_service.execute_tailor_pipeline,
        t_job,
        payload.job_description or "",
        payload.required_skills or [],
    )
    
    return {
        "status": "accepted",
        "tailor_job_id": t_job.id,
        "job_id": t_job.job_id,
        "company_name": t_job.company_name,
        "message": f"Tailoring job '{t_job.id}' queued for background execution.",
    }


@router.get("/{tailor_job_id}")
async def get_tailor_status(tailor_job_id: str) -> dict:
    """Returns the current status, alignment metrics, truthfulness report, and LaTeX of a tailoring job."""
    t_job = resume_service.get_tailor_job(tailor_job_id)
    if not t_job:
        raise HTTPException(status_code=404, detail=f"Tailor job '{tailor_job_id}' not found.")
    return t_job.model_dump(mode="json")


@router.post("/{tailor_job_id}/revalidate")
async def revalidate_tailor_job(tailor_job_id: str, payload: RevalidateRequest) -> dict:
    """
    Guard-AGAIN revalidation (P7-H3).
    Re-runs TruthfulnessGuard audits on user-edited LaTeX before approving or recompiling PDF.
    """
    t_job = resume_service.get_tailor_job(tailor_job_id)
    if not t_job:
        raise HTTPException(status_code=404, detail=f"Tailor job '{tailor_job_id}' not found.")
    
    updated = await resume_service.revalidate_and_recompile(t_job, payload.edited_latex)
    return updated.model_dump(mode="json")


@router.get("/{tailor_job_id}/pdf")
async def download_tailored_pdf(tailor_job_id: str):
    """Downloads the compiled PDF artifact for an approved tailoring job (Blocked if validation failed)."""
    t_job = resume_service.get_tailor_job(tailor_job_id)
    if not t_job:
        raise HTTPException(status_code=404, detail=f"Tailor job '{tailor_job_id}' not found.")
    
    if t_job.status == TailorJobStatus.REJECTED_VALIDATION or not t_job.validation.passed:
        raise HTTPException(
            status_code=400,
            detail="Cannot download PDF: Truthfulness validation failed or artifact contains ungrounded claims.",
        )

    if not t_job.pdf_path or not os.path.exists(t_job.pdf_path):
        raise HTTPException(status_code=404, detail="PDF artifact not yet generated or compilation pending.")
    
    return FileResponse(
        path=t_job.pdf_path,
        filename=os.path.basename(t_job.pdf_path),
        media_type="application/pdf",
    )
