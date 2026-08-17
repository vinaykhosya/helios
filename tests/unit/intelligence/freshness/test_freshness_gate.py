"""
tests/unit/intelligence/freshness/test_freshness_gate.py

Comprehensive test suite for Helios v3.0 Freshness Intelligence & Job Age Gate.
Tests boundary conditions, repost vs update semantics, timezone handling,
anomaly detection, and Ready-to-Apply gate invariant.
"""
import pytest
from datetime import datetime, timedelta, timezone

from core.models.job import Job, JobSource, FreshnessStatus, FreshnessConfidence
from intelligence.freshness.gate import (
    FreshnessGate,
    FreshnessSettings,
    parse_timestamp,
)


@pytest.fixture
def gate():
    return FreshnessGate(FreshnessSettings(ready_max_age_days=7, aging_max_age_days=14, stale_max_age_days=30))


@pytest.fixture
def ref_now():
    return datetime(2026, 8, 17, 12, 0, 0)


# ── 1. Boundary Condition Tests (0, 1, 7, 8, 14, 15, 30, 31 days) ───────────

def test_boundary_0_days_today(gate, ref_now):
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="1",
        source_url="https://boards.greenhouse.io/test/1",
        title="AI Engineer",
        company="Anthropic",
        posted_at=ref_now,
        fit_score=0.90,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 0
    assert evaluated.freshness_status == FreshnessStatus.FRESH
    assert evaluated.freshness_reference_at == ref_now
    assert gate.is_ready_to_apply(evaluated) is True


def test_boundary_7_days_fresh_cutoff(gate, ref_now):
    job = Job(
        source=JobSource.ASHBY,
        source_id="2",
        source_url="https://ashbyhq.com/test/2",
        title="Backend Engineer",
        company="Linear",
        posted_at=ref_now - timedelta(days=7),
        fit_score=0.85,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 7
    assert evaluated.freshness_status == FreshnessStatus.FRESH
    assert gate.is_ready_to_apply(evaluated) is True


def test_boundary_8_days_aging(gate, ref_now):
    job = Job(
        source=JobSource.LEVER,
        source_id="3",
        source_url="https://jobs.lever.co/test/3",
        title="Full Stack Engineer",
        company="Spotify",
        posted_at=ref_now - timedelta(days=8),
        fit_score=0.95,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 8
    assert evaluated.freshness_status == FreshnessStatus.AGING
    # Invariant #14: 8-day-old job must NOT be Ready-to-Apply
    assert gate.is_ready_to_apply(evaluated) is False


def test_boundary_14_days_aging_limit(gate, ref_now):
    job = Job(
        source=JobSource.LINKEDIN,
        source_id="4",
        source_url="https://linkedin.com/jobs/4",
        title="ML Engineer",
        company="Google",
        posted_at=ref_now - timedelta(days=14),
        fit_score=0.92,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 14
    assert evaluated.freshness_status == FreshnessStatus.AGING
    assert gate.is_ready_to_apply(evaluated) is False


def test_boundary_15_days_stale(gate, ref_now):
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="5",
        source_url="https://boards.greenhouse.io/test/5",
        title="Software Engineer",
        company="Stripe",
        posted_at=ref_now - timedelta(days=15),
        fit_score=0.98,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 15
    assert evaluated.freshness_status == FreshnessStatus.STALE
    assert gate.is_ready_to_apply(evaluated) is False


def test_boundary_31_days_very_stale(gate, ref_now):
    job = Job(
        source=JobSource.ASHBY,
        source_id="6",
        source_url="https://ashbyhq.com/test/6",
        title="Staff Engineer",
        company="Notion",
        posted_at=ref_now - timedelta(days=31),
        fit_score=0.99,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 31
    assert evaluated.freshness_status == FreshnessStatus.VERY_STALE
    assert gate.is_ready_to_apply(evaluated) is False


# ── 2. Reposting vs Ordinary Update Semantics ───────────────────────────────

def test_confirmed_repost_resets_freshness(gate, ref_now):
    """A job posted 30d ago with a verified repost 2d ago becomes FRESH."""
    job = Job(
        source=JobSource.LINKEDIN,
        source_id="7",
        source_url="https://linkedin.com/jobs/7",
        title="Data Engineer",
        company="Meta",
        posted_at=ref_now - timedelta(days=30),
        is_reposted=True,
        reposted_at=ref_now - timedelta(days=2),
        fit_score=0.88,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 2
    assert evaluated.freshness_status == FreshnessStatus.FRESH
    assert evaluated.freshness_confidence == FreshnessConfidence.CONFIRMED_REPOSTED
    assert evaluated.freshness_reference_at == ref_now - timedelta(days=2)
    assert gate.is_ready_to_apply(evaluated) is True


def test_ordinary_update_does_not_reset_freshness(gate, ref_now):
    """A job posted 30d ago with last_updated_at=yesterday remains VERY_STALE."""
    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="8",
        source_url="https://boards.greenhouse.io/test/8",
        title="AI Engineer",
        company="OpenAI",
        posted_at=ref_now - timedelta(days=30),
        last_updated_at=ref_now - timedelta(days=1),
        is_reposted=False,
        fit_score=0.96,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 30
    assert evaluated.freshness_status == FreshnessStatus.STALE or evaluated.freshness_status == FreshnessStatus.VERY_STALE
    assert evaluated.freshness_reference_at == ref_now - timedelta(days=30)
    assert gate.is_ready_to_apply(evaluated) is False


# ── 3. Missing & Malformed Timestamp Handling (Fail-Closed) ─────────────────

def test_missing_date_is_unknown_and_fails_closed(gate, ref_now):
    job = Job(
        source=JobSource.MANUAL,
        source_id="9",
        source_url="https://test.com/9",
        title="Software Engineer",
        company="Startup",
        posted_at=None,
        posted_date=None,
        fit_score=0.95,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days is None
    assert evaluated.freshness_status == FreshnessStatus.UNKNOWN
    assert evaluated.freshness_confidence == FreshnessConfidence.UNKNOWN
    # Must fail closed for Ready-to-Apply
    assert gate.is_ready_to_apply(evaluated) is False


def test_malformed_string_date_fails_closed(gate, ref_now):
    dt, conf, anomaly = parse_timestamp("posted whenever maybe random gibberish")
    assert dt is None
    assert conf == FreshnessConfidence.UNKNOWN
    assert anomaly == "MALFORMED_INPUT"


# ── 4. Future Timestamp Handling & Anomaly Flagging ──────────────────────────

def test_future_timestamp_clamped_with_anomaly(gate, ref_now):
    future_dt = ref_now + timedelta(days=2)
    job = Job(
        source=JobSource.ASHBY,
        source_id="10",
        source_url="https://ashbyhq.com/test/10",
        title="Systems Engineer",
        company="Ramp",
        posted_at=future_dt,
        fit_score=0.88,
        apply_url="https://apply.url",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 0
    assert evaluated.freshness_status == FreshnessStatus.FRESH
    assert evaluated.date_anomaly == "FUTURE_TIMESTAMP"


# ── 5. Timezone & Relative String Parsing ───────────────────────────────────

def test_timezone_aware_timestamp_parsed_to_utc(ref_now):
    # 2026-08-15 17:00:00 -07:00 == 2026-08-16 00:00:00 UTC
    iso_str = "2026-08-15T17:00:00-07:00"
    dt, conf, anomaly = parse_timestamp(iso_str, now_dt=ref_now)
    assert dt is not None
    assert dt == datetime(2026, 8, 16, 0, 0, 0)
    assert conf == FreshnessConfidence.CONFIRMED_POSTED
    assert anomaly is None


def test_relative_strings_parsed_correctly(ref_now):
    dt_2d, conf, _ = parse_timestamp("2 days ago", now_dt=ref_now)
    assert dt_2d == ref_now - timedelta(days=2)
    assert conf == FreshnessConfidence.INFERRED

    dt_1w, _, _ = parse_timestamp("1 week ago", now_dt=ref_now)
    assert dt_1w == ref_now - timedelta(weeks=1)

    dt_3h, _, _ = parse_timestamp("3 hours ago", now_dt=ref_now)
    assert dt_3h == ref_now - timedelta(hours=3)

    dt_yest, _, _ = parse_timestamp("yesterday", now_dt=ref_now)
    assert dt_yest == ref_now - timedelta(days=1)


# ── 6. 96% Stale vs 81% Fresh Verification Requirement ─────────────────────

def test_96_pct_match_posted_20_days_ago_is_not_ready_to_apply(gate, ref_now):
    """Requirement: 96% match posted 20 days ago is NOT Ready-to-Apply."""
    stale_high_fit = Job(
        source=JobSource.GREENHOUSE,
        source_id="11",
        source_url="https://boards.greenhouse.io/test/11",
        title="Senior AI Engineer",
        company="Anthropic",
        posted_at=ref_now - timedelta(days=20),
        fit_score=0.96,
        eligibility_status="ELIGIBLE",
        friction_level="LOW",
        apply_url="https://anthropic.com/apply",
    )
    evaluated = gate.evaluate_job(stale_high_fit, current_time=ref_now)
    assert evaluated.fit_score == 0.96  # Score remains UNTOUCHED
    assert evaluated.age_days == 20
    assert evaluated.freshness_status == FreshnessStatus.STALE
    assert gate.is_ready_to_apply(evaluated) is False


def test_81_pct_match_posted_2_days_ago_is_ready_to_apply(gate, ref_now):
    """Requirement: 81% match posted 2 days ago IS Ready-to-Apply."""
    fresh_moderate_fit = Job(
        source=JobSource.ASHBY,
        source_id="12",
        source_url="https://ashbyhq.com/test/12",
        title="Software Engineer",
        company="Vercel",
        posted_at=ref_now - timedelta(days=2),
        fit_score=0.81,
        eligibility_status="ELIGIBLE",
        friction_level="LOW",
        apply_url="https://vercel.com/apply",
    )
    evaluated = gate.evaluate_job(fresh_moderate_fit, current_time=ref_now)
    assert evaluated.fit_score == 0.81
    assert evaluated.age_days == 2
    assert evaluated.freshness_status == FreshnessStatus.FRESH
    assert gate.is_ready_to_apply(evaluated) is True


# ── 7. Canonical Merge Resolution Rule ──────────────────────────────────────

def test_canonical_merge_keeps_earlier_genuine_date():
    existing = {"posted_at": datetime(2026, 8, 10, 10, 0), "freshness_reference_at": datetime(2026, 8, 10, 10, 0)}
    incoming = {"posted_at": datetime(2026, 8, 14, 10, 0), "freshness_reference_at": datetime(2026, 8, 14, 10, 0), "is_reposted": False}
    merged = FreshnessGate.resolve_canonical_dates(existing, incoming)
    assert merged["posted_at"] == datetime(2026, 8, 10, 10, 0)
    assert merged["freshness_reference_at"] == datetime(2026, 8, 10, 10, 0)


def test_canonical_merge_with_confirmed_repost_uses_repost_date(gate, ref_now):
    """
    Edge case verification:
      Source A: original post 30 days ago
      Source B: confirmed repost 2 days ago
      Resulting job must evaluate to FRESH (age = 2 days).
    """
    source_a_existing = {
        "posted_at": ref_now - timedelta(days=30),
        "freshness_reference_at": ref_now - timedelta(days=30),
        "is_reposted": False,
    }
    source_b_incoming = {
        "posted_at": ref_now - timedelta(days=30),
        "is_reposted": True,
        "reposted_at": ref_now - timedelta(days=2),
        "freshness_confidence": FreshnessConfidence.CONFIRMED_REPOSTED,
    }
    merged = FreshnessGate.resolve_canonical_dates(source_a_existing, source_b_incoming)
    assert merged["is_reposted"] is True
    assert merged["freshness_reference_at"] == ref_now - timedelta(days=2)
    assert merged["freshness_confidence"] == FreshnessConfidence.CONFIRMED_REPOSTED

    # Evaluate the merged record with FreshnessGate
    job = Job(
        source=JobSource.LINKEDIN,
        source_id="repost-merge-1",
        source_url="https://linkedin.com/jobs/view/123",
        title="Senior Backend Engineer",
        company="Stripe",
        posted_at=merged.get("posted_at"),
        is_reposted=merged.get("is_reposted"),
        reposted_at=merged.get("reposted_at"),
        freshness_confidence=merged.get("freshness_confidence"),
        fit_score=0.92,
        apply_url="https://stripe.com/apply",
    )
    evaluated = gate.evaluate_job(job, current_time=ref_now)
    assert evaluated.age_days == 2
    assert evaluated.freshness_status == FreshnessStatus.FRESH
    assert gate.is_ready_to_apply(evaluated) is True
