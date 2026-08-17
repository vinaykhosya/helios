"""
backend/src/api/profiles.py

FastAPI route handlers for Candidate Profiles & Master LaTeX Resume Management.
Supports switching active profile lenses (AI/ML, Backend, Fullstack),
updating skills, locations, constraints, and live LaTeX templates.
"""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from core.models.candidate_profile import CandidateProfile
from backend.src.services.profile_service import profile_service

router = APIRouter(prefix="/api/v1/profiles", tags=["Profiles"])


class ActivateProfileRequest(BaseModel):
    profile_id: str


class UpdateResumeTemplateRequest(BaseModel):
    profile_id: Optional[str] = None
    latex_content: str


@router.get("", response_model=List[dict])
async def list_profiles() -> List[dict]:
    """Returns all available candidate profile lenses."""
    return profile_service.get_all_profiles()


@router.get("/active")
async def get_active_profile() -> dict:
    """Returns the currently active candidate profile lens."""
    p = profile_service.get_active_profile()
    return {
        "id": p.id,
        "profile_name": p.profile_name,
        "name": p.name,
        "email": p.email,
        "phone": p.phone,
        "location": p.location,
        "target_roles": p.ideal_role_keywords,
        "target_locations": p.target_locations,
        "tech_stack": p.required_tech_stack,
        "max_experience_years": p.max_experience_years,
        "graduation_year": p.graduation_year,
        "years_of_experience": p.years_of_experience,
        "education_summary": p.education_summary,
        "preferred_industries": p.preferred_industries,
    }


@router.post("/activate")
async def activate_profile(payload: ActivateProfileRequest) -> dict:
    """Switches the active candidate profile lens across discovery, ranking, and AI tailoring."""
    try:
        active = profile_service.activate_profile(payload.profile_id)
        return {
            "status": "success",
            "active_profile_id": active.id,
            "profile_name": active.profile_name,
            "message": f"Activated profile lens '{active.profile_name}'.",
        }
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{profile_id}")
async def get_profile(profile_id: str) -> dict:
    """Returns details for a specific profile ID."""
    p = profile_service.get_profile_by_id(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Profile '{profile_id}' not found.")
    return p.model_dump(mode="json")


@router.get("/resume/template")
async def get_resume_template(profile_id: Optional[str] = None) -> dict:
    """Returns the master LaTeX resume markup string."""
    tex = profile_service.get_master_resume_latex(profile_id)
    return {"status": "success", "latex": tex}


@router.post("/resume/template")
async def save_resume_template(payload: UpdateResumeTemplateRequest) -> dict:
    """Saves modified LaTeX resume markup string."""
    ok = profile_service.save_master_resume_latex(payload.latex_content, payload.profile_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to save LaTeX template.")
    return {"status": "success", "message": "Master LaTeX template saved successfully."}
