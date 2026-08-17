"""
intelligence/friction/scorer.py

FrictionScorer -- quantifies how hard it is to submit to a specific ATS.
Stateless. No network calls. No LLM. Fast.

Score bands:
  0 STANDARD  -- name, email, resume upload only
  1 MODERATE  -- 1-3 short custom questions
  2 HEAVY     -- 4+ questions, multi-page, login required
  3 BLOCKING  -- CAPTCHA, OTP, video, account creation
                 -> Always routes to HUMAN_QUEUE regardless of fit score
"""
from __future__ import annotations
from pydantic import BaseModel, Field


class FrictionResult(BaseModel):
    score: int = Field(..., ge=0, le=3)
    label: str      # "STANDARD" | "MODERATE" | "HEAVY" | "BLOCKING"
    reasons: list[str] = Field(default_factory=list)


class FrictionScorer:
    LABELS = {0: "STANDARD", 1: "MODERATE", 2: "HEAVY", 3: "BLOCKING"}

    def score(
        self,
        ats_name: str = "unknown",
        custom_questions: list[str] | None = None,
        page_count: int = 1,
        has_captcha: bool = False,
        has_otp: bool = False,
        requires_login: bool = False,
        requires_account_creation: bool = False,
        has_essay_questions: bool = False,
        has_video_questions: bool = False,
    ) -> FrictionResult:
        reasons: list[str] = []
        score = 0

        if has_captcha:
            reasons.append("CAPTCHA detected"); score = max(score, 3)
        if has_otp:
            reasons.append("OTP / 2FA required"); score = max(score, 3)
        if requires_account_creation:
            reasons.append("Account creation required"); score = max(score, 3)
        if has_video_questions:
            reasons.append("Video response required"); score = max(score, 3)
        if has_essay_questions:
            reasons.append("Essay questions present"); score = max(score, 2)
        if requires_login:
            reasons.append("Login required"); score = max(score, 2)
        if page_count >= 3:
            reasons.append(f"Multi-page form ({page_count} pages)"); score = max(score, 2)

        q_count = len(custom_questions or [])
        if q_count >= 4:
            reasons.append(f"{q_count} custom questions"); score = max(score, 2)
        elif q_count >= 1:
            reasons.append(f"{q_count} short question(s)"); score = max(score, 1)

        return FrictionResult(score=score, label=self.LABELS[score], reasons=reasons)
