"""
intelligence/ranking/ranker.py

RankingAgent — Multi-dimensional soft scoring engine ("Should Vinay apply?").
Computes overall fit score, confidence rating, missing skills, and application recommendation.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, RemotePolicy
from intelligence.ranking.skill_extractor import SkillExtractor
from intelligence.ranking.skill_match_scorer import SkillMatchScorer


class MatchDimension(BaseModel):
    """
    Scored dimension of job fit.
    """
    name: str = Field(..., description="Dimension name (e.g. 'Tech Stack')")
    score: float = Field(..., description="Score contribution 0.0 to 1.0")
    weight: float = Field(..., description="Dimension weight in overall score")
    matched: bool = Field(..., description="True if dimension meets threshold")


class RankingResult(BaseModel):
    """
    Complete output of the RankingAgent.
    """
    job_id: str
    overall_score: float = Field(..., description="Weighted average fit score 0.0 to 1.0")
    confidence: float = Field(..., description="System confidence score 0.0 to 1.0")
    dimensions: list[MatchDimension] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommendation: str = Field(..., description="'auto_apply' | 'ask_user' | 'review'")
    reason: str = Field(..., description="Human-readable match explanation")


class RankingAgent:
    """
    Multi-dimensional soft scoring agent.
    """

    def __init__(self, profile: CandidateProfile):
        self.profile = profile
        self.skill_extractor = SkillExtractor()
        self.skill_scorer = SkillMatchScorer()

    def rank(self, job: Job) -> RankingResult:
        """
        Calculates multi-dimensional score and recommendation for a job.
        """
        dimensions: list[MatchDimension] = []

        # Dimension 1: Tech Stack Match (Weight: 0.40)
        job_skills = self.skill_extractor.extract_from_job(job)
        candidate_skills = self.skill_extractor.extract_from_profile(self.profile)
        skill_result = self.skill_scorer.score(job_skills, candidate_skills)

        dimensions.append(MatchDimension(
            name="Tech Stack",
            score=skill_result.overall_score,
            weight=0.40,
            matched=skill_result.overall_score >= 0.5,
        ))

        # Dimension 2: Location Match (Weight: 0.20)
        is_remote = (job.remote == RemotePolicy.REMOTE or str(job.remote) == "remote")
        location_matched = is_remote or any(
            target.lower() in (job.location or "").lower() for target in self.profile.target_locations
        )
        loc_score = 1.0 if location_matched else 0.0
        dimensions.append(MatchDimension(
            name="Location",
            score=loc_score,
            weight=0.20,
            matched=location_matched,
        ))

        # Dimension 3: Seniority & Experience Match (Weight: 0.20)
        exp_req = job.experience_years if job.experience_years is not None else 1.0
        exp_score = 1.0 if exp_req <= self.profile.max_experience_years else 0.4
        dimensions.append(MatchDimension(
            name="Seniority",
            score=exp_score,
            weight=0.20,
            matched=exp_score >= 0.8,
        ))

        # Dimension 4: Role Keyword Match (Weight: 0.20)
        title_lower = (job.title or "").lower()
        role_matched = any(
            role_kw.lower() in title_lower for role_kw in self.profile.ideal_role_keywords
        )
        role_score = 1.0 if role_matched else 0.5
        dimensions.append(MatchDimension(
            name="Role Title",
            score=role_score,
            weight=0.20,
            matched=role_matched,
        ))

        # Calculate weighted overall score
        overall_score = sum(d.score * d.weight for d in dimensions)
        overall_score = round(overall_score, 3)

        # Confidence calculation
        confidence = min(round(overall_score * 1.1, 3), 1.0)

        # Recommendation decision
        if confidence >= 0.95:
            recommendation = "auto_apply"
        elif confidence >= 0.80:
            recommendation = "ask_user"
        else:
            recommendation = "review"

        reason = f"Overall fit: {int(overall_score * 100)}%. Tech match: {int(skill_result.overall_score * 100)}%."

        return RankingResult(
            job_id=str(job.id),
            overall_score=overall_score,
            confidence=confidence,
            dimensions=dimensions,
            missing_skills=skill_result.missing_skills,
            recommendation=recommendation,
            reason=reason,
        )
