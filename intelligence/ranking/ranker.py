"""
intelligence/ranking/ranker.py

RankingAgent — Multi-dimensional soft scoring engine ("Should Vinay apply?").
Computes overall fit score, confidence rating, missing skills, and application recommendation.
"""
from __future__ import annotations

import re
from typing import Optional, Any
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

    Dimensions and weights (must sum to 1.0):
      1. Tech Stack   — 0.35
      2. Location     — 0.20
      3. Seniority    — 0.20
      4. Role Title   — 0.10
      5. Semantic     — 0.15  (fallback 0.5 until SemanticScorer wired in Phase 7)
    """

    DIMENSION_WEIGHTS = {
        "Tech Stack": 0.35,
        "Location": 0.20,
        "Seniority": 0.20,
        "Role Title": 0.10,
        "Semantic": 0.15,
    }

    def __init__(self, profile: CandidateProfile, semantic_scorer: Optional[Any] = None):
        self.profile = profile
        self.skill_extractor = SkillExtractor()
        self.skill_scorer = SkillMatchScorer()
        self._semantic_scorer = semantic_scorer

    def rank(
        self,
        job: Job,
        embedding_id: str = "",
        job_vector: Optional[list[float]] = None,
    ) -> RankingResult:
        """
        Calculates multi-dimensional score and recommendation for a job.

        Args:
            job:          The job to rank.
            embedding_id: The stored embedding ID for this job (from EmbeddingGenerated event).
                          Empty string ("") means embedding is unavailable — semantic score
                          falls back to 0.5 (neutral contribution).
            job_vector:   Optional direct precomputed float vector.
        """
        dimensions: list[MatchDimension] = []

        # Dimension 1: Tech Stack Match (Weight: 0.35)
        job_skills = self.skill_extractor.extract_from_job(job)
        candidate_skills = self.skill_extractor.extract_from_profile(self.profile)
        skill_result = self.skill_scorer.score(job_skills, candidate_skills)
        dimensions.append(MatchDimension(
            name="Tech Stack",
            score=skill_result.overall_score,
            weight=self.DIMENSION_WEIGHTS["Tech Stack"],
            matched=skill_result.overall_score >= 0.5,
        ))

        # Dimension 2: Location Match (Weight: 0.20)
        location_score = self._compute_location_score(job)
        dimensions.append(MatchDimension(
            name="Location",
            score=location_score,
            weight=self.DIMENSION_WEIGHTS["Location"],
            matched=location_score >= 0.7,
        ))

        # Dimension 3: Seniority Match (Weight: 0.20)
        seniority_score = self._compute_seniority_score(job)
        dimensions.append(MatchDimension(
            name="Seniority",
            score=seniority_score,
            weight=self.DIMENSION_WEIGHTS["Seniority"],
            matched=seniority_score >= 0.7,
        ))

        # Dimension 4: Role Keyword Match (Weight: 0.10)
        title_lower = (job.title or "").lower()
        role_matched = any(
            role_kw.lower() in title_lower for role_kw in self.profile.ideal_role_keywords
        )
        role_score = 1.0 if role_matched else 0.5
        dimensions.append(MatchDimension(
            name="Role Title",
            score=role_score,
            weight=self.DIMENSION_WEIGHTS["Role Title"],
            matched=role_matched,
        ))

        # Dimension 5: Semantic Match (Weight: 0.15)
        semantic_score = self._compute_semantic_score(embedding_id, job_vector)
        dimensions.append(MatchDimension(
            name="Semantic",
            score=semantic_score,
            weight=self.DIMENSION_WEIGHTS["Semantic"],
            matched=semantic_score >= 0.5,
        ))

        # Validate weights sum to 1.0 (guards against future drift)
        total_weight = sum(d.weight for d in dimensions)
        assert abs(total_weight - 1.0) < 1e-6, (
            f"RankingAgent dimension weights must sum to 1.0, got {total_weight:.4f}"
        )

        # Calculate weighted overall score
        overall_score = sum(d.score * d.weight for d in dimensions)
        overall_score = round(overall_score, 3)

        # Build dimension breakdown dict for UI display
        breakdown = {
            "tech_stack": skill_result.overall_score,
            "location": location_score,
            "seniority": seniority_score,
            "role": role_score,
            "semantic": semantic_score,
        }
        job.dimension_breakdown = breakdown

        # Confidence calculation
        confidence = min(round(overall_score * 1.1, 3), 1.0)

        # Seniority / Eligibility Status Evaluation
        is_seniority_mismatch = seniority_score < 0.7
        if is_seniority_mismatch:
            job.eligibility_status = "SENIORITY_MISMATCH"
            job.eligibility_reasons = [f"Required experience exceeds profile ({self.profile.max_experience_years} yrs max)"]
            recommendation = "seniority_review"
            reason = f"Seniority Mismatch. Overall fit: {int(overall_score * 100)}% (Tech: {int(skill_result.overall_score * 100)}%)."
        else:
            if confidence >= 0.95:
                recommendation = "auto_apply"
            elif confidence >= 0.80:
                recommendation = "ask_user"
            else:
                recommendation = "review"
            reason = f"Overall fit: {int(overall_score * 100)}%. Tech match: {int(skill_result.overall_score * 100)}%."

        job.fit_score = overall_score

        return RankingResult(
            job_id=str(job.id),
            overall_score=overall_score,
            confidence=confidence,
            dimensions=dimensions,
            missing_skills=skill_result.missing_skills,
            recommendation=recommendation,
            reason=reason,
        )

    def _compute_semantic_score(
        self,
        embedding_id: str,
        job_vector: Optional[list[float]] = None,
    ) -> float:
        """
        Returns the semantic similarity score for this job.
        Uses injected SemanticScorer if available, otherwise returns 0.5 (neutral fallback).
        """
        if self._semantic_scorer is not None and (embedding_id or job_vector):
            try:
                return float(self._semantic_scorer.score(embedding_id, job_vector=job_vector))
            except Exception as e:
                print(f"[RankingAgent] SemanticScorer fallback: {e}")
                return 0.5
        return 0.5   # neutral fallback

    def _compute_location_score(self, job: Job) -> float:
        is_remote = (job.remote == RemotePolicy.REMOTE or str(job.remote) == "remote")
        location_matched = is_remote or any(
            target.lower() in (job.location or "").lower() for target in self.profile.target_locations
        )
        return 1.0 if location_matched else 0.0

    def _compute_seniority_score(self, job: Job) -> float:
        """
        Computes seniority match score (0.0 to 1.0) evaluating both explicit experience
        numbers and title seniority keywords against the candidate's profile limit.
        """
        title_lower = (job.title or "").lower()
        desc_lower = (job.description or "").lower()
        full_text = f"{title_lower}\n{desc_lower}"
        title_norm = re.sub(r'[^a-zA-Z0-9\s]', ' ', title_lower)
        
        # 1. Hard senior title prefixes
        hard_senior_keywords = [
            "senior", "sr", "staff", "principal", "lead", "director",
            "manager", "mgr", "head of", "vp", "vice president", "fellow", "expert", "distinguished"
        ]
        has_hard_senior_title = any(
            re.search(rf"\b{re.escape(kw)}\b", title_norm) for kw in hard_senior_keywords
        )

        # 2. Architect title (Seniority Risk)
        has_architect_title = bool(re.search(r"\barchitect\b", title_norm))

        # 3. Numeric experience check
        exp_req = job.experience_years
        if exp_req is None:
            # Check for explicit experience strings in full text (e.g., "5+ years", "6-8 yrs")
            if any(k in full_text for k in ["5+", "6+", "7+", "8+", "10+", "5-8 yrs", "5-7 yrs", "6-10 yrs", "7-10 years", "5+ yrs", "5+ years", "8+ years"]):
                exp_req = 5.0
            elif any(k in full_text for k in ["3-5 yrs", "3-5 years", "4+ yrs", "4+ years"]):
                exp_req = 4.0
            else:
                exp_req = 1.0

        # Evaluate against candidate max experience (e.g. 3 years)
        if exp_req > self.profile.max_experience_years:
            return 0.3

        if has_hard_senior_title and self.profile.max_experience_years <= 3:
            return 0.3

        if has_architect_title:
            # If architect title has senior prefix or requires 4+ yrs -> mismatch
            if has_hard_senior_title or exp_req >= 4:
                return 0.3
            return 0.8  # early-career / generic architect title

        return 1.0
