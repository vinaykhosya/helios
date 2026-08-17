"""
integrations/gmail/matcher.py

EmailApplicationMatcher — finds which application an email belongs to.

Matching hierarchy (most to least specific):
  Level 1: Tracking token or application ID in email subject/body (EXACT)
  Level 2: Job URL / requisition ID mentioned in email (EXACT)
  Level 3: Company + role title both mentioned in subject/body (STRONG if unique, AMBIGUOUS if multiple)
  Level 4: Sender domain + company name in subject (PROBABLE if unique, AMBIGUOUS if multiple)
  Level 5: Sender domain only (PROBABLE if unique, AMBIGUOUS if multiple)

Whenever MULTIPLE applications match at any level:
  → result is AMBIGUOUS → NO-OP → no application state is mutated.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import re
from typing import Optional


class MatchConfidence(str, Enum):
    EXACT     = "exact"       # Level 1–2 — safe to mutate
    STRONG    = "strong"      # Level 3 — safe to mutate
    PROBABLE  = "probable"    # Level 4–5 single match — safe to mutate
    AMBIGUOUS = "ambiguous"   # Multiple matching candidates — NO-OP
    NO_MATCH  = "no_match"    # No candidate found


@dataclass
class MatchResult:
    confidence: MatchConfidence
    application_id: Optional[str]
    application_ids_considered: list[str]
    matched_on: str

    @property
    def safe_to_mutate(self) -> bool:
        return self.confidence in (
            MatchConfidence.EXACT,
            MatchConfidence.STRONG,
            MatchConfidence.PROBABLE,
        ) and self.application_id is not None

    @property
    def is_ambiguous(self) -> bool:
        return self.confidence == MatchConfidence.AMBIGUOUS


class EmailApplicationMatcher:

    def match(
        self,
        sender_email: str,
        sender_domain: str,
        subject: str,
        body_preview: str,
        open_applications: list[dict],
        # Each dict: {id, company_domain, company_name, job_title, apply_url, status}
    ) -> MatchResult:
        if not open_applications:
            return MatchResult(
                confidence=MatchConfidence.NO_MATCH,
                application_id=None,
                application_ids_considered=[],
                matched_on="no_open_applications",
            )

        combined_text = (subject + " " + body_preview).lower()

        # Level 1: Tracking token / explicit application ID in email
        l1_matches = self._match_by_token(combined_text, open_applications)
        if len(l1_matches) == 1:
            return MatchResult(
                confidence=MatchConfidence.EXACT,
                application_id=l1_matches[0]["id"],
                application_ids_considered=[l1_matches[0]["id"]],
                matched_on="tracking_token_in_email",
            )
        elif len(l1_matches) > 1:
            return MatchResult(
                confidence=MatchConfidence.AMBIGUOUS,
                application_id=None,
                application_ids_considered=[a["id"] for a in l1_matches],
                matched_on="tracking_token_ambiguous",
            )

        # Level 2: Job URL in email
        l2_matches = self._match_by_url(combined_text, open_applications)
        if len(l2_matches) == 1:
            return MatchResult(
                confidence=MatchConfidence.EXACT,
                application_id=l2_matches[0]["id"],
                application_ids_considered=[l2_matches[0]["id"]],
                matched_on="job_url_in_email",
            )
        elif len(l2_matches) > 1:
            return MatchResult(
                confidence=MatchConfidence.AMBIGUOUS,
                application_id=None,
                application_ids_considered=[a["id"] for a in l2_matches],
                matched_on="job_url_ambiguous",
            )

        # Level 3: Company + Role in subject or body (ambiguity safe)
        l3_candidates = self._match_by_company_and_role(combined_text, open_applications)
        if len(l3_candidates) == 1:
            return MatchResult(
                confidence=MatchConfidence.STRONG,
                application_id=l3_candidates[0]["id"],
                application_ids_considered=[l3_candidates[0]["id"]],
                matched_on="company_and_role_single",
            )
        elif len(l3_candidates) > 1:
            return MatchResult(
                confidence=MatchConfidence.AMBIGUOUS,
                application_id=None,
                application_ids_considered=[a["id"] for a in l3_candidates],
                matched_on=f"company_and_role_ambiguous_{len(l3_candidates)}_candidates",
            )

        # Level 4: Sender domain + company name in subject (must be unique)
        l4_candidates = self._match_by_domain_and_subject(sender_domain, subject, open_applications)
        if len(l4_candidates) == 1:
            return MatchResult(
                confidence=MatchConfidence.PROBABLE,
                application_id=l4_candidates[0]["id"],
                application_ids_considered=[l4_candidates[0]["id"]],
                matched_on="domain_and_subject_single",
            )
        elif len(l4_candidates) > 1:
            return MatchResult(
                confidence=MatchConfidence.AMBIGUOUS,
                application_id=None,
                application_ids_considered=[a["id"] for a in l4_candidates],
                matched_on=f"domain_and_subject_ambiguous_{len(l4_candidates)}_candidates",
            )

        # Level 5: Sender domain only (must be unique)
        domain_candidates = [
            a for a in open_applications
            if a.get("company_domain", "").lower() == sender_domain.lower()
        ]
        if len(domain_candidates) == 1:
            return MatchResult(
                confidence=MatchConfidence.PROBABLE,
                application_id=domain_candidates[0]["id"],
                application_ids_considered=[domain_candidates[0]["id"]],
                matched_on="domain_only_single",
            )
        elif len(domain_candidates) > 1:
            # Multiple applications to same company = AMBIGUOUS = NO-OP
            return MatchResult(
                confidence=MatchConfidence.AMBIGUOUS,
                application_id=None,
                application_ids_considered=[a["id"] for a in domain_candidates],
                matched_on=(
                    f"domain_only_ambiguous: {len(domain_candidates)} applications "
                    f"to {sender_domain}"
                ),
            )

        return MatchResult(
            confidence=MatchConfidence.NO_MATCH,
            application_id=None,
            application_ids_considered=[],
            matched_on="no_domain_match",
        )

    def _match_by_token(self, combined_text: str, apps: list[dict]) -> list[dict]:
        matched = []
        for app in apps:
            app_id = (app.get("id") or "").lower()
            if app_id and (app_id in combined_text or f"helios-{app_id}" in combined_text):
                matched.append(app)
        return matched

    def _match_by_url(self, combined_text: str, apps: list[dict]) -> list[dict]:
        matched = []
        for app in apps:
            url = (app.get("apply_url") or "").lower()
            if url and len(url) > 20 and url in combined_text:
                matched.append(app)
        return matched

    def _match_by_company_and_role(
        self, combined_text: str, apps: list[dict]
    ) -> list[dict]:
        matched = []
        for app in apps:
            company = (app.get("company_name") or "").lower()
            role = (app.get("job_title") or "").lower()
            if company and role and company in combined_text and role in combined_text:
                matched.append(app)
        return matched

    def _match_by_domain_and_subject(
        self, domain: str, subject: str, apps: list[dict]
    ) -> list[dict]:
        subj = subject.lower()
        return [
            a for a in apps
            if a.get("company_domain", "").lower() == domain.lower()
            and a.get("company_name", "").lower() in subj
        ]
