"""
automation/confidence.py

ConfidenceEngine — Evaluates match ranking and form complexity to determine application execution mode:
AUTO_APPLY (≥0.95), ASK_USER (0.80-0.94), or REVIEW (<0.80).
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field

from intelligence.ranking.ranker import RankingResult


class ApplicationDecision(str, Enum):
    AUTO_APPLY = "auto_apply"   # High match & standard form -> apply unattended
    ASK_USER   = "ask_user"     # Medium/high match -> Telegram notification with 1-click approval
    REVIEW     = "review"       # Low match or complex form -> push to manual review queue


class ConfidenceEngine(BaseModel):
    """
    Determines application automation safety level based on ranking confidence and form complexity.
    """

    AUTO_APPLY_THRESHOLD: float = 0.95
    ASK_USER_THRESHOLD: float = 0.80

    def decide(
        self,
        ranking_result: RankingResult,
        form_complexity: int = 0,
    ) -> ApplicationDecision:
        """
        Calculates application decision.

        Args:
            ranking_result: RankingResult from RankingAgent.
            form_complexity: Penalty score (0 = standard form, 1 = custom questions, 2 = complex).

        Returns:
            ApplicationDecision enum value.
        """
        complexity_penalty = form_complexity * 0.05
        adjusted_confidence = round(ranking_result.confidence - complexity_penalty, 3)

        if adjusted_confidence >= self.AUTO_APPLY_THRESHOLD:
            return ApplicationDecision.AUTO_APPLY
        elif adjusted_confidence >= self.ASK_USER_THRESHOLD:
            return ApplicationDecision.ASK_USER
        else:
            return ApplicationDecision.REVIEW
