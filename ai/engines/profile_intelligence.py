"""
ai/engines/profile_intelligence.py

ProfileIntelligenceAgent — Single source of truth for structured candidate data.
Provides candidate information, skill prioritization per JD, and bullet point selection.
"""
from __future__ import annotations

from typing import Optional
from core.config.profile_loader import load_candidate_profile
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job


class ProfileIntelligenceAgent:
    """
    Maintains candidate profile state and prepares context for resume and cover letter generation.
    """

    def __init__(self, profile: Optional[CandidateProfile] = None):
        self.profile = profile or load_candidate_profile()

    def get_profile(self) -> CandidateProfile:
        """Returns the active candidate profile."""
        return self.profile

    def get_skills_for_job(self, job: Job) -> list[str]:
        """
        Prioritizes skills matching the job description first.
        """
        all_skills = list(dict.fromkeys(self.profile.required_tech_stack + self.profile.ideal_role_keywords))
        jd_text = f"{job.title} {job.description or ''} {' '.join(job.skills or [])}".lower()

        matching_skills = [s for s in all_skills if s.lower() in jd_text]
        other_skills = [s for s in all_skills if s.lower() not in jd_text]

        return matching_skills + other_skills

    def get_experience_bullets(self, job: Job, max_bullets: int = 5) -> list[str]:
        """
        Selects experience bullet points, prioritizing those relevant to the target job description.
        """
        bullets = self.profile.experience_bullets
        if not bullets:
            return []

        jd_text = f"{job.title} {job.description or ''} {' '.join(job.skills or [])}".lower()

        # Score bullets by keyword overlap with JD
        scored_bullets = []
        for bullet in bullets:
            score = sum(1 for word in bullet.lower().split() if len(word) > 3 and word in jd_text)
            scored_bullets.append((score, bullet))

        # Sort by score descending
        scored_bullets.sort(key=lambda x: x[0], reverse=True)
        return [b for _, b in scored_bullets[:max_bullets]]
