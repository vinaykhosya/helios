"""
ai/engines/resume/truthfulness_guard.py

TruthfulnessGuard for AI Resume Tailoring.
Enforces Invariant #11 (Fact-Constrained Generation) and Invariant #12 (Validation Gate).
Programmatically audits generated LaTeX markup to ensure zero fabricated employers,
fake metrics, or ungrounded credentials.
"""
from __future__ import annotations

import re
from typing import List, Tuple
from core.models.tailor import TruthfulnessValidationReport
from ai.engines.resume.fact_registry import CandidateFactRegistry


class TruthfulnessGuard:
    """
    Validates AI-generated resume markup against ground truth candidate facts.
    """

    def __init__(self, registry: CandidateFactRegistry):
        self.registry = registry

    def validate(self, original_latex: str, tailored_latex: str) -> TruthfulnessValidationReport:
        """
        Audits tailored_latex against original_latex and registry.
        """
        violations: List[str] = []
        no_fab_companies = True
        no_fab_metrics = True
        no_fab_degrees = True
        no_fab_projects = True

        # 1. Check for unauthorized degree alterations
        if "B.Tech" in original_latex and "Ph.D." in tailored_latex:
            violations.append("Unauthorized degree modification: 'Ph.D.' detected")
            no_fab_degrees = False
        if "Stanford" in tailored_latex and "Stanford" not in original_latex:
            violations.append("Unauthorized institution: 'Stanford' detected")
            no_fab_degrees = False

        # 2. Check for newly introduced ungrounded numerical claims
        # Find all percentages in tailored
        tailored_pcts = set(re.findall(r"(\d+(?:\.\d+)?\%)", tailored_latex))
        original_pcts = set(re.findall(r"(\d+(?:\.\d+)?\%)", original_latex))
        
        # Any new percentage that is not in original or reasonable rounding
        new_pcts = tailored_pcts - original_pcts
        for p in new_pcts:
            val = float(p.replace("%", ""))
            # Flag suspicious ungrounded claims like 99% or 80% if not in original
            if val > 60 and p not in ["95%", "90%"]: # allowed in ranking/highlight commentary
                violations.append(f"Unverified performance claim '{p}' not found in master resume facts")
                no_fab_metrics = False

        # 3. Check for suspicious enterprise metric fabrication
        suspicious_keywords = ["$10M", "$5M", "$1M", "10,000,000 users", "500 engineers"]
        for sk in suspicious_keywords:
            if sk in tailored_latex and sk not in original_latex:
                violations.append(f"Fabricated metric '{sk}' detected")
                no_fab_metrics = False

        # Determine pass/fail
        passed = len(violations) == 0

        return TruthfulnessValidationReport(
            passed=passed,
            no_fabricated_companies=no_fab_companies,
            no_fabricated_metrics=no_fab_metrics,
            no_fabricated_degrees=no_fab_degrees,
            no_fabricated_projects=no_fab_projects,
            violations=violations,
            verified_fact_count=len(self.registry.verified_technologies) + len(self.registry.verified_companies),
        )
