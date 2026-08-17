"""
intelligence/ranking/skill_match_scorer.py

SkillMatchScorer — Computes overlap score and missing skills vector.
"""
from __future__ import annotations

from typing import Any, Optional, Dict, List
from pydantic import BaseModel, Field


class SkillMatchScore(BaseModel):
    """
    Detailed output of skill matching analysis.
    """
    overall_score: float = Field(..., description="0.0 to 1.0 match ratio")
    matched_skills: list[str] = Field(default_factory=list, description="Skills present in both JD and candidate profile")
    missing_skills: list[str] = Field(default_factory=list, description="Skills present in JD but missing in candidate profile")
    breakdown: dict[str, Any] = Field(default_factory=dict, description="Skill match weights and scores")
    has_technical_requirements: bool = Field(default=True, description="False if no technical skills were detected in JD")


class SkillMatchScorer:
    """
    Scores tech stack similarity between job requirements and candidate profile.
    """

    def score(
        self,
        job_skills: list[str],
        candidate_skills: list[str],
    ) -> SkillMatchScore:
        """
        Computes match score, matched skills, and missing skills.
        Absence of technical requirements evaluates to 0.0, never 1.0.
        """
        if not job_skills:
            return SkillMatchScore(
                overall_score=0.0,
                matched_skills=[],
                missing_skills=[],
                breakdown={"matched_count": 0.0, "total_job_skills": 0.0, "ratio": 0.0, "has_technical_requirements": False},
                has_technical_requirements=False,
            )

        job_set = {s.lower(): s for s in job_skills}
        cand_set = {s.lower() for s in candidate_skills}

        matched = []
        missing = []

        for norm_skill, orig_skill in job_set.items():
            if norm_skill in cand_set:
                matched.append(orig_skill)
            else:
                missing.append(orig_skill)

        overall_score = round(len(matched) / len(job_set), 3)

        breakdown = {
            "matched_count": float(len(matched)),
            "total_job_skills": float(len(job_set)),
            "ratio": overall_score,
        }

        return SkillMatchScore(
            overall_score=overall_score,
            matched_skills=sorted(matched),
            missing_skills=sorted(missing),
            breakdown=breakdown,
        )
