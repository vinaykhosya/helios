"""
intelligence/ranking/eligibility.py

EligibilityGate — Binary pass/fail filter using candidate hard constraints.
Runs fast local rules with ZERO LLM calls or network latency.
"""
from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, Field

from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, RemotePolicy



class EligibilityResult(BaseModel):
    """
    Structured outcome of an eligibility check.
    """
    eligible: bool = Field(..., description="True if job passes all hard constraint rules")
    rejection_reasons: list[str] = Field(default_factory=list, description="Human-readable list of rejection reasons")


class RejectionStats(BaseModel):
    """
    Aggregated stats for a batch of processed jobs.
    """
    total_scanned: int = 0
    total_eligible: int = 0
    rejection_counts: dict[str, int] = Field(default_factory=dict)


class EligibilityGate:
    """
    Evaluates jobs against hard binary constraints.
    Does not use LLMs or database calls — designed for high throughput.
    """

    EXP_REGEX = re.compile(r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience", re.IGNORECASE)

    def __init__(self, profile: CandidateProfile):
        self.profile = profile

    def check(self, job: Job) -> EligibilityResult:
        """
        Runs all 7 hard rules against the given job.
        Returns EligibilityResult immediately.
        """
        reasons: list[str] = []

        title_lower = (job.title or "").lower()
        desc_lower = (job.description or "").lower()
        comp_lower = (job.company or "").lower()
        loc_lower = (job.location or "").lower()

        # Rule 1: Excluded Keywords in Title
        for kw in self.profile.excluded_keywords:
            if kw.lower() in title_lower:
                reasons.append(f"Title contains excluded keyword: '{kw}'")

        # Rule 2: Excluded Keywords in Description
        for kw in self.profile.excluded_keywords:
            if kw.lower() in desc_lower:
                reasons.append(f"Description contains excluded keyword: '{kw}'")

        # Rule 3: Excluded Company
        for exc_comp in self.profile.excluded_companies:
            if exc_comp.lower() in comp_lower:
                reasons.append(f"Company '{job.company}' is on exclusion list")

        # Rule 4: Required Tech Stack
        if self.profile.required_tech_stack:
            job_skills_lower = [s.lower() for s in (job.skills or [])]
            has_required_tech = any(
                tech.lower() in desc_lower or tech.lower() in title_lower or tech.lower() in job_skills_lower
                for tech in self.profile.required_tech_stack
            )
            if not has_required_tech:
                reasons.append(f"No required tech stack found: {self.profile.required_tech_stack}")

        # Rule 5: Location Match
        is_remote = (job.remote == RemotePolicy.REMOTE or str(job.remote) == "remote")
        if job.location and not is_remote and self.profile.target_locations:
            loc_matched = any(
                target.lower() in loc_lower for target in self.profile.target_locations
            )
            if not loc_matched:
                reasons.append(f"Location '{job.location}' not in target locations {self.profile.target_locations}")


        # Rule 6: Experience Range
        if job.description:
            matches = self.EXP_REGEX.findall(job.description)
            if matches:
                req_years = max(int(m) for m in matches)
                if req_years > self.profile.max_experience_years:
                    reasons.append(f"Requires {req_years}+ years experience, max configured is {self.profile.max_experience_years}")

        # Rule 7: Employment Type
        if job.employment_type and self.profile.job_types:
            emp_type_val = job.employment_type.value if hasattr(job.employment_type, "value") else str(job.employment_type)
            if emp_type_val.lower() not in [t.lower() for t in self.profile.job_types]:
                reasons.append(f"Employment type '{emp_type_val}' not in accepted types {self.profile.job_types}")

        # Deduplicate reasons if any keyword matched both title and description
        unique_reasons = list(dict.fromkeys(reasons))
        is_eligible = len(unique_reasons) == 0

        return EligibilityResult(eligible=is_eligible, rejection_reasons=unique_reasons)

    async def filter_batch(self, jobs: list[Job]) -> tuple[list[Job], list[EligibilityResult]]:
        """
        Process a list of jobs through the EligibilityGate.

        Returns:
            Tuple of (eligible_jobs, all_results)
        """
        eligible_jobs = []
        all_results = []
        for job in jobs:
            res = self.check(job)
            all_results.append(res)
            if res.eligible:
                eligible_jobs.append(job)
        return eligible_jobs, all_results

    def summarize_session(self, results: list[EligibilityResult]) -> RejectionStats:
        """
        Aggregates rejection statistics for reporting.
        """
        stats = RejectionStats(total_scanned=len(results))
        for res in results:
            if res.eligible:
                stats.total_eligible += 1
            else:
                for reason in res.rejection_reasons:
                    # Categorize reason header
                    category = reason.split(":")[0] if ":" in reason else reason
                    stats.rejection_counts[category] = stats.rejection_counts.get(category, 0) + 1
        return stats
