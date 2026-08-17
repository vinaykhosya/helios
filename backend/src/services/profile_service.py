"""
backend/src/services/profile_service.py

Multi-Profile Service for Helios.
Manages profile lenses (AI/ML, Backend, Fullstack, Data, DevOps),
custom eligibility constraints, resume templates, and candidate embeddings.
"""
from __future__ import annotations

import os
from typing import Dict, List, Optional
from core.models.candidate_profile import CandidateProfile, MultiProfileConfig
from core.config.profile_loader import load_candidate_profile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MASTER_TEX_PATH = os.path.join(BASE_DIR, "templates", "master_resume.tex")


class ProfileService:
    def __init__(self):
        self._config = self._initialize_profiles()

    def _initialize_profiles(self) -> MultiProfileConfig:
        """Initializes default multi-role profiles for candidate Vinay Khosya."""
        base_p = load_candidate_profile()

        # Load master LaTeX
        master_latex = ""
        if os.path.exists(MASTER_TEX_PATH):
            with open(MASTER_TEX_PATH, "r", encoding="utf-8") as f:
                master_latex = f.read()

        ai_ml_profile = CandidateProfile(
            id="ai_ml",
            profile_name="AI & ML Systems Engineer",
            name=base_p.name,
            email=base_p.email,
            phone=base_p.phone,
            location=base_p.location,
            linkedin_url="https://linkedin.com/in/vinaykhosya",
            github_url="https://github.com/vinaykhosya",
            portfolio_url="https://vinaykhosya.com",
            willing_to_relocate=True,
            requires_sponsorship=False,
            graduation_year=2027,
            years_of_experience=1.0,
            max_experience_years=3.0,
            required_tech_stack=["Python", "PyTorch", "FastAPI", "ONNX", "OpenCV"],
            excluded_keywords=["PHP", "Sales", "Staffing", "Unpaid", "Telecaller"],
            target_locations=["India", "Delhi", "Gurugram", "Noida", "Bangalore", "Hyderabad", "Pune", "Remote"],
            excluded_companies=["BadCompanyInc"],
            job_types=["full_time", "internship"],
            experience_bullets=base_p.experience_bullets,
            education_summary="B.Tech in Artificial Intelligence and Data Science (NSUT Delhi, 2023-2027)",
            preferred_company_sizes=["startup", "mid_size", "enterprise"],
            preferred_industries=["AI", "DeepTech", "FinTech", "SaaS"],
            ideal_role_keywords=["AI Engineer", "Machine Learning Engineer", "AI Systems Engineer", "LLM Engineer", "Applied Scientist"],
            resume_template_path="templates/master_resume.tex",
            master_resume_latex=master_latex,
        )

        backend_profile = CandidateProfile(
            id="backend",
            profile_name="Backend Systems Engineer",
            name=base_p.name,
            email=base_p.email,
            phone=base_p.phone,
            location=base_p.location,
            linkedin_url="https://linkedin.com/in/vinaykhosya",
            github_url="https://github.com/vinaykhosya",
            portfolio_url="https://vinaykhosya.com",
            willing_to_relocate=True,
            requires_sponsorship=False,
            graduation_year=2027,
            years_of_experience=1.0,
            max_experience_years=3.0,
            required_tech_stack=["Python", "FastAPI", "PostgreSQL", "Supabase", "Redis", "Docker", "SQLAlchemy"],
            excluded_keywords=["PHP", "WordPress", "Sales", "Unpaid"],
            target_locations=["India", "Delhi", "Gurugram", "Noida", "Bangalore", "Hyderabad", "Pune", "Remote"],
            excluded_companies=[],
            job_types=["full_time", "internship"],
            experience_bullets=base_p.experience_bullets,
            education_summary="B.Tech in Computer Science / AI (NSUT Delhi, 2023-2027)",
            preferred_company_sizes=["startup", "mid_size", "enterprise"],
            preferred_industries=["SaaS", "FinTech", "Developer Tools", "AI Infrastructure"],
            ideal_role_keywords=["Backend Engineer", "Software Development Engineer", "SDE 1", "Python Developer", "Systems Engineer"],
            resume_template_path="templates/master_resume.tex",
            master_resume_latex=master_latex,
        )

        fullstack_profile = CandidateProfile(
            id="fullstack",
            profile_name="Full Stack Engineer",
            name=base_p.name,
            email=base_p.email,
            phone=base_p.phone,
            location=base_p.location,
            linkedin_url="https://linkedin.com/in/vinaykhosya",
            github_url="https://github.com/vinaykhosya",
            portfolio_url="https://vinaykhosya.com",
            willing_to_relocate=True,
            requires_sponsorship=False,
            graduation_year=2027,
            years_of_experience=1.0,
            max_experience_years=3.0,
            required_tech_stack=["React", "TypeScript", "Python", "FastAPI", "PostgreSQL", "Tailwind CSS"],
            excluded_keywords=["WordPress", "Wix", "Sales", "Unpaid"],
            target_locations=["India", "Delhi", "Gurugram", "Noida", "Bangalore", "Remote"],
            excluded_companies=[],
            job_types=["full_time", "internship"],
            experience_bullets=base_p.experience_bullets,
            education_summary="B.Tech in Computer Science / AI (NSUT Delhi, 2023-2027)",
            preferred_company_sizes=["startup", "mid_size"],
            preferred_industries=["SaaS", "Product", "Tech"],
            ideal_role_keywords=["Full Stack Developer", "Software Engineer", "Frontend & Backend Engineer"],
            resume_template_path="templates/master_resume.tex",
            master_resume_latex=master_latex,
        )

        return MultiProfileConfig(
            active_profile_id="ai_ml",
            profiles={
                "ai_ml": ai_ml_profile,
                "backend": backend_profile,
                "fullstack": fullstack_profile,
            }
        )

    def get_all_profiles(self) -> List[dict]:
        return [
            {
                "id": p.id,
                "profile_name": p.profile_name,
                "name": p.name,
                "email": p.email,
                "target_roles": p.ideal_role_keywords,
                "target_locations": p.target_locations,
                "tech_stack": p.required_tech_stack,
                "max_experience_years": p.max_experience_years,
                "is_active": p.id == self._config.active_profile_id,
            }
            for p in self._config.profiles.values()
        ]

    def get_active_profile(self) -> CandidateProfile:
        active_id = self._config.active_profile_id
        return self._config.profiles.get(active_id, list(self._config.profiles.values())[0])

    def get_profile_by_id(self, profile_id: str) -> Optional[CandidateProfile]:
        return self._config.profiles.get(profile_id)

    def activate_profile(self, profile_id: str) -> CandidateProfile:
        if profile_id not in self._config.profiles:
            raise KeyError(f"Profile '{profile_id}' does not exist.")
        self._config.active_profile_id = profile_id
        return self.get_active_profile()

    def update_profile(self, profile: CandidateProfile) -> CandidateProfile:
        self._config.profiles[profile.id] = profile
        return profile

    def get_master_resume_latex(self, profile_id: Optional[str] = None) -> str:
        target_p = self.get_profile_by_id(profile_id) if profile_id else self.get_active_profile()
        if target_p and target_p.master_resume_latex:
            return target_p.master_resume_latex
        if os.path.exists(MASTER_TEX_PATH):
            with open(MASTER_TEX_PATH, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def save_master_resume_latex(self, latex_content: str, profile_id: Optional[str] = None) -> bool:
        target_p = self.get_profile_by_id(profile_id) if profile_id else self.get_active_profile()
        if target_p:
            updated = target_p.model_copy(update={"master_resume_latex": latex_content})
            self._config.profiles[target_p.id] = updated

        # Also persist to master_resume.tex on disk
        try:
            with open(MASTER_TEX_PATH, "w", encoding="utf-8") as f:
                f.write(latex_content)
            return True
        except Exception as e:
            print(f"[ProfileService] Could not write master_resume.tex to disk: {e}")
            return False


# Global singleton instance
profile_service = ProfileService()
