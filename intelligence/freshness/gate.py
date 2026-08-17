"""
intelligence/freshness/gate.py

Helios v3.0 Freshness Intelligence Engine & Job Age Gate.
Orthogonal operational gate evaluating posting age, repost provenance,
and availability without altering underlying 5-dimension Match Scores.
"""
from __future__ import annotations

import re
import math
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union, Dict
from pydantic import BaseModel, Field

from core.models.job import Job, FreshnessStatus, FreshnessConfidence


class FreshnessSettings(BaseModel):
    """Configurable server-side age thresholds."""
    ready_max_age_days: int = Field(default=7, description="Hard cutoff for Ready-to-Apply queue (default: 7)")
    aging_max_age_days: int = Field(default=14, description="Boundary for Aging status (default: 14)")
    stale_max_age_days: int = Field(default=30, description="Boundary for Stale status (default: 30)")


DEFAULT_FRESHNESS_SETTINGS = FreshnessSettings()


def parse_timestamp(raw_value: Any, now_dt: Optional[datetime] = None) -> tuple[Optional[datetime], FreshnessConfidence, Optional[str]]:
    """
    Parses diverse ATS timestamp formats:
      - ISO-8601 strings (e.g. '2026-08-15T10:30:00Z', '2026-08-10T23:30-07:00')
      - Unix timestamps / Epoch milliseconds (e.g. 1723700000, 1723700000000)
      - Relative strings (e.g. '2 days ago', '1 week ago', '3 hours ago', 'yesterday')

    Returns:
        (parsed_datetime_utc_naive, confidence, anomaly_flag)
    """
    if raw_value is None:
        return None, FreshnessConfidence.UNKNOWN, None

    now = now_dt or datetime.utcnow()

    # 1. Native datetime
    if isinstance(raw_value, datetime):
        dt = raw_value
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        anomaly = "FUTURE_TIMESTAMP" if dt > now else None
        return dt, FreshnessConfidence.CONFIRMED_POSTED, anomaly

    # 2. Numeric epoch (seconds or milliseconds)
    if isinstance(raw_value, (int, float)):
        try:
            val = float(raw_value)
            if val > 1e11:  # Epoch milliseconds
                val = val / 1000.0
            dt = datetime.utcfromtimestamp(val)
            anomaly = "FUTURE_TIMESTAMP" if dt > now else None
            return dt, FreshnessConfidence.CONFIRMED_POSTED, anomaly
        except Exception:
            return None, FreshnessConfidence.UNKNOWN, "MALFORMED_INPUT"

    # 3. String parsing
    if isinstance(raw_value, str):
        val_str = raw_value.strip()
        if not val_str:
            return None, FreshnessConfidence.UNKNOWN, None

        # Numeric string epoch
        if val_str.isdigit():
            try:
                num = int(val_str)
                if num > 1e11:
                    num = num / 1000.0
                dt = datetime.utcfromtimestamp(num)
                anomaly = "FUTURE_TIMESTAMP" if dt > now else None
                return dt, FreshnessConfidence.CONFIRMED_POSTED, anomaly
            except Exception:
                pass

        # Relative string parsing (e.g. '2 days ago', '1 week ago', '3 hours ago', 'yesterday', 'just now')
        s_lower = val_str.lower()
        if re.search(r"\b(just now|today)\b", s_lower):
            return now, FreshnessConfidence.INFERRED, None
        if re.search(r"\byesterday\b", s_lower) and len(s_lower.split()) <= 3:
            return now - timedelta(days=1), FreshnessConfidence.INFERRED, None

        # Regex for relative quantities
        rel_match = re.search(r"(\d+)\s*\+?\s*(second|sec|minute|min|hour|hr|day|week|month|year)s?\s*(?:ago)?", s_lower)
        if rel_match:
            qty = int(rel_match.group(1))
            unit = rel_match.group(2)
            if unit.startswith("sec"):
                return now - timedelta(seconds=qty), FreshnessConfidence.INFERRED, None
            elif unit.startswith("min"):
                return now - timedelta(minutes=qty), FreshnessConfidence.INFERRED, None
            elif unit.startswith("hour") or unit.startswith("hr"):
                return now - timedelta(hours=qty), FreshnessConfidence.INFERRED, None
            elif unit.startswith("day"):
                return now - timedelta(days=qty), FreshnessConfidence.INFERRED, None
            elif unit.startswith("week"):
                return now - timedelta(weeks=qty), FreshnessConfidence.INFERRED, None
            elif unit.startswith("month"):
                return now - timedelta(days=qty * 30), FreshnessConfidence.INFERRED, None
            elif unit.startswith("year"):
                return now - timedelta(days=qty * 365), FreshnessConfidence.INFERRED, None

        if "30+ days ago" in s_lower or ">30 days ago" in s_lower:
            return now - timedelta(days=35), FreshnessConfidence.INFERRED, None

        # Standard ISO-8601 string parsing
        try:
            # Handle ISO formats
            clean_str = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean_str)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            anomaly = "FUTURE_TIMESTAMP" if dt > now else None
            return dt, FreshnessConfidence.CONFIRMED_POSTED, anomaly
        except ValueError:
            pass

        # Try common datetime formats
        for fmt in (
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M:%S",
            "%Y/%m/%d",
            "%d-%m-%Y",
            "%b %d, %Y",
            "%B %d, %Y",
            "%d %b %Y",
            "%d %B %Y",
        ):
            try:
                dt = datetime.strptime(val_str, fmt)
                anomaly = "FUTURE_TIMESTAMP" if dt > now else None
                return dt, FreshnessConfidence.CONFIRMED_POSTED, anomaly
            except ValueError:
                continue

    return None, FreshnessConfidence.UNKNOWN, "MALFORMED_INPUT"


class FreshnessGate:
    """
    Evaluates and enforces freshness rules across the Helios pipeline.
    """

    def __init__(self, settings: Optional[FreshnessSettings] = None):
        self.settings = settings or DEFAULT_FRESHNESS_SETTINGS

    def evaluate_job(self, job: Job, current_time: Optional[datetime] = None) -> Job:
        """
        Classifies job freshness, calculates auditable age_days and reference timestamp.
        """
        now = current_time or datetime.utcnow()

        # 1. Determine canonical reference timestamp
        ref_dt: Optional[datetime] = None
        confidence = FreshnessConfidence.UNKNOWN
        anomaly: Optional[str] = None

        # Check for confirmed reposting first
        if job.is_reposted and job.reposted_at:
            ref_dt, confidence, anomaly = parse_timestamp(job.reposted_at, now_dt=now)
            confidence = FreshnessConfidence.CONFIRMED_REPOSTED
        elif job.posted_at:
            ref_dt, confidence, anomaly = parse_timestamp(job.posted_at, now_dt=now)
            if job.freshness_confidence != FreshnessConfidence.UNKNOWN:
                confidence = job.freshness_confidence
        elif job.posted_date:
            ref_dt, confidence, anomaly = parse_timestamp(job.posted_date, now_dt=now)
        elif job.raw_data and isinstance(job.raw_data, dict):
            # Attempt to extract from raw ATS payload
            raw_candidates = [
                job.raw_data.get("publishedAt"),
                job.raw_data.get("publishedDate"),
                job.raw_data.get("posted_at"),
                job.raw_data.get("createdAt"),
                job.raw_data.get("first_published"),
            ]
            for c in raw_candidates:
                if c:
                    parsed_dt, conf, anom = parse_timestamp(c, now_dt=now)
                    if parsed_dt:
                        ref_dt = parsed_dt
                        confidence = conf
                        anomaly = anom
                        break

        # 2. If no valid date found: fail-closed to UNKNOWN
        if ref_dt is None:
            job.freshness_reference_at = None
            job.age_days = None
            job.freshness_status = FreshnessStatus.UNKNOWN
            job.freshness_confidence = FreshnessConfidence.UNKNOWN
            job.date_anomaly = anomaly or "MISSING_DATE"
            return job

        # 3. Calculate exact age in days
        job.freshness_reference_at = ref_dt
        job.freshness_confidence = confidence

        delta_seconds = (now - ref_dt).total_seconds()
        if delta_seconds < 0:
            # Future timestamp clamp
            job.age_days = 0
            job.date_anomaly = "FUTURE_TIMESTAMP"
        else:
            job.age_days = max(0, int(delta_seconds / 86400.0))
            job.date_anomaly = anomaly

        # 4. Classify Freshness Status according to settings
        age = job.age_days
        if age <= self.settings.ready_max_age_days:
            job.freshness_status = FreshnessStatus.FRESH
        elif age <= self.settings.aging_max_age_days:
            job.freshness_status = FreshnessStatus.AGING
        elif age <= self.settings.stale_max_age_days:
            job.freshness_status = FreshnessStatus.STALE
        else:
            job.freshness_status = FreshnessStatus.VERY_STALE

        return job

    def is_ready_to_apply(self, job: Union[Job, Dict[str, Any]]) -> bool:
        """
        Hard Invariant #14 Gate:
          Job is READY_TO_APPLY iff:
            1. eligibility_status == 'ELIGIBLE'
            2. fit_score >= 0.80
            3. freshness_status == 'FRESH' (age_days <= ready_max_age_days)
            4. age_days is NOT None and age_days <= ready_max_age_days
            5. friction_level in ['LOW', 'MEDIUM']
            6. valid apply_url
            7. not closed (availability != 'CLOSED')
            8. application_status not in ['APPLIED', 'SKIPPED']
        """
        if isinstance(job, Job):
            fit = job.fit_score or 0.0
            elig = job.eligibility_status == "ELIGIBLE"
            fresh = job.freshness_status == FreshnessStatus.FRESH
            age_ok = job.age_days is not None and job.age_days <= self.settings.ready_max_age_days
            friction_ok = job.friction_level in ["LOW", "MEDIUM"]
            url_ok = bool(job.apply_url and job.apply_url.strip() and job.apply_url.strip() != "#")
            avail_ok = (not job.is_closed) and (job.availability != "CLOSED")
            status_ok = job.application_status not in ["APPLIED", "SKIPPED"]
            return elig and (fit >= 0.80) and fresh and age_ok and friction_ok and url_ok and avail_ok and status_ok
        elif isinstance(job, dict):
            fit = job.get("fit_score") or (float(str(job.get("Match Fit", "0%")).replace("%", "")) / 100.0)
            elig = job.get("eligibility_status", "ELIGIBLE") == "ELIGIBLE"
            fresh_stat = job.get("freshness_status", "UNKNOWN")
            age_days = job.get("age_days")
            fresh = (fresh_stat == "FRESH") or (age_days is not None and age_days <= self.settings.ready_max_age_days)
            age_ok = age_days is not None and age_days <= self.settings.ready_max_age_days
            friction = job.get("friction_level", "LOW")
            friction_ok = friction in ["LOW", "MEDIUM"]
            apply_url = job.get("apply_url") or job.get("Apply Link")
            url_ok = bool(apply_url and apply_url.strip() and apply_url.strip() != "#")
            avail_ok = (not job.get("is_closed", False)) and (job.get("availability", "OPEN") != "CLOSED")
            app_status = job.get("application_status", "NOT_APPLIED")
            status_ok = app_status not in ["APPLIED", "SKIPPED"]
            return elig and (fit >= 0.80) and fresh and age_ok and friction_ok and url_ok and avail_ok and status_ok
        return False

    @staticmethod
    def resolve_canonical_dates(existing_dict: dict, incoming_dict: dict) -> dict:
        """
        Deduplication date merge rule:
          - If EITHER record is a confirmed repost (`CONFIRMED_REPOSTED` or `is_reposted=True`),
            the genuine repost date supersedes older initial posting dates.
          - Otherwise (ordinary updates or initial posts), canonical posting timestamp
            is the EARLIER genuine date to prevent artificial rejuvenation.
        """
        ex_is_repost = bool(existing_dict.get("is_reposted") or existing_dict.get("freshness_confidence") in [FreshnessConfidence.CONFIRMED_REPOSTED, "CONFIRMED_REPOSTED", "FreshnessConfidence.CONFIRMED_REPOSTED"])
        in_is_repost = bool(incoming_dict.get("is_reposted") or incoming_dict.get("freshness_confidence") in [FreshnessConfidence.CONFIRMED_REPOSTED, "CONFIRMED_REPOSTED", "FreshnessConfidence.CONFIRMED_REPOSTED"])

        ex_dt = existing_dict.get("reposted_at") if ex_is_repost else (existing_dict.get("freshness_reference_at") or existing_dict.get("posted_at"))
        in_dt = incoming_dict.get("reposted_at") if in_is_repost else (incoming_dict.get("freshness_reference_at") or incoming_dict.get("posted_at"))

        if isinstance(ex_dt, str):
            ex_dt, _, _ = parse_timestamp(ex_dt)
        if isinstance(in_dt, str):
            in_dt, _, _ = parse_timestamp(in_dt)

        # 1. If incoming is a confirmed repost, it overrides
        if in_is_repost and in_dt:
            incoming_dict["is_reposted"] = True
            incoming_dict["reposted_at"] = in_dt
            incoming_dict["freshness_reference_at"] = in_dt
            incoming_dict["freshness_confidence"] = FreshnessConfidence.CONFIRMED_REPOSTED
            return incoming_dict

        # 2. If existing was a confirmed repost and incoming is not, keep existing repost date
        if ex_is_repost and ex_dt:
            incoming_dict["is_reposted"] = True
            incoming_dict["reposted_at"] = ex_dt
            incoming_dict["freshness_reference_at"] = ex_dt
            incoming_dict["freshness_confidence"] = FreshnessConfidence.CONFIRMED_REPOSTED
            return incoming_dict

        # 3. Neither is a confirmed repost: earlier genuine date wins to prevent artificial rejuvenation
        if ex_dt and in_dt:
            earlier_dt = min(ex_dt, in_dt)
            incoming_dict["posted_at"] = earlier_dt
            incoming_dict["freshness_reference_at"] = earlier_dt
        elif ex_dt and not in_dt:
            incoming_dict["posted_at"] = ex_dt
            incoming_dict["freshness_reference_at"] = ex_dt
        elif in_dt and not ex_dt:
            incoming_dict["posted_at"] = in_dt
            incoming_dict["freshness_reference_at"] = in_dt

        return incoming_dict
