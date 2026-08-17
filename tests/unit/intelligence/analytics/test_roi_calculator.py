"""
tests/unit/intelligence/analytics/test_roi_calculator.py

Unit tests for ROICalculator pure functions and funnel metrics.
"""
from datetime import datetime, timedelta
from core.models.application import Application, ApplicationStatus
from intelligence.analytics.roi_calculator import ROICalculator, FunnelMetrics


def test_empty_applications_returns_zero_metrics():
    calc = ROICalculator()
    metrics = calc.compute([])
    assert metrics.total_applications == 0
    assert metrics.submitted_total == 0
    assert metrics.response_rate == 0.0
    assert metrics.positive_response_rate == 0.0
    assert metrics.offer_rate == 0.0
    assert metrics.avg_days_to_response is None


def test_funnel_metrics_realistic_cohort():
    """
    Test 10 submitted applications cohort:
      - 3 awaiting response (submitted_manual)
      - 3 rejections
      - 2 phone screens
      - 1 technical interview
      - 1 offer
      - 2 in pending queue (not yet submitted)
    """
    now = datetime.utcnow()
    applied_t = now - timedelta(days=5)

    apps = [
        # Awaiting response (3)
        Application(id="s1", user_id="u1", job_id="j1", status=ApplicationStatus.SUBMITTED_MANUAL, applied_at=applied_t),
        Application(id="s2", user_id="u1", job_id="j2", status=ApplicationStatus.SUBMITTED_MANUAL, applied_at=applied_t),
        Application(id="s3", user_id="u1", job_id="j3", status=ApplicationStatus.APPLIED, applied_at=applied_t),
        # Outcomes: Rejections (3)
        Application(id="r1", user_id="u1", job_id="j4", status=ApplicationStatus.REJECTED, applied_at=applied_t, updated_at=now - timedelta(days=3)),
        Application(id="r2", user_id="u1", job_id="j5", status=ApplicationStatus.REJECTED, applied_at=applied_t, updated_at=now - timedelta(days=2)),
        Application(id="r3", user_id="u1", job_id="j6", status=ApplicationStatus.REJECTED, applied_at=applied_t, updated_at=now - timedelta(days=1)),
        # Outcomes: Positive responses (4)
        Application(id="p1", user_id="u1", job_id="j7", status=ApplicationStatus.PHONE_SCREEN, applied_at=applied_t, updated_at=now - timedelta(days=2)),
        Application(id="p2", user_id="u1", job_id="j8", status=ApplicationStatus.PHONE_SCREEN, applied_at=applied_t, updated_at=now - timedelta(days=1)),
        Application(id="t1", user_id="u1", job_id="j9", status=ApplicationStatus.TECHNICAL, applied_at=applied_t, updated_at=now - timedelta(days=1)),
        Application(id="o1", user_id="u1", job_id="j10", status=ApplicationStatus.OFFER, applied_at=applied_t, updated_at=now),
        # Discovered / In Queue (not submitted yet) (2)
        Application(id="q1", user_id="u1", job_id="j11", status=ApplicationStatus.PENDING_MANUAL),
        Application(id="q2", user_id="u1", job_id="j12", status=ApplicationStatus.PENDING_MANUAL),
    ]

    calc = ROICalculator()
    m = calc.compute(apps)

    assert m.total_applications == 12
    assert m.pending_manual == 2
    assert m.submitted_total == 10
    assert m.no_response == 3
    assert m.rejections == 3
    assert m.phone_screens == 2
    assert m.technical_interviews == 1
    assert m.offers == 1
    assert m.responses == 7
    assert m.positive_responses == 4

    # Rates: bounded 0.0 <= rate <= 1.0
    assert m.response_rate == 0.70           # 7 responses / 10 submitted = 70%
    assert m.positive_response_rate == 0.40  # 4 positive / 10 submitted = 40%
    assert m.offer_rate == 0.10              # 1 offer / 10 submitted = 10%

    assert m.avg_days_to_response is not None
    assert 0.0 < m.avg_days_to_response <= 5.0
