"""
intelligence/analytics/roi_calculator.py

ROICalculator — computes application funnel and conversion metrics.
Pure functions: no DB access, no network calls.
Accepts a list of Application domain objects.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class FunnelMetrics:
    total_applications: int
    pending_manual: int
    automation_queued: int
    submitted_total: int
    submitted_manual: int
    applied: int
    no_response: int
    responses: int
    rejections: int
    positive_responses: int
    phone_screens: int
    technical_interviews: int
    offers: int
    response_rate: float            # responses / submitted_total (0.0 - 1.0)
    positive_response_rate: float   # positive_responses / submitted_total (0.0 - 1.0)
    offer_rate: float               # offers / submitted_total (0.0 - 1.0)
    avg_days_to_response: Optional[float]


class ROICalculator:

    def compute(self, applications: list) -> FunnelMetrics:
        total = len(applications)
        if total == 0:
            return FunnelMetrics(
                total_applications=0,
                pending_manual=0,
                automation_queued=0,
                submitted_total=0,
                submitted_manual=0,
                applied=0,
                no_response=0,
                responses=0,
                rejections=0,
                positive_responses=0,
                phone_screens=0,
                technical_interviews=0,
                offers=0,
                response_rate=0.0,
                positive_response_rate=0.0,
                offer_rate=0.0,
                avg_days_to_response=None,
            )

        counts: dict[str, int] = {}
        for app in applications:
            status = app.status if isinstance(app.status, str) else getattr(app.status, "value", str(app.status))
            counts[status] = counts.get(status, 0) + 1

        pending_manual = counts.get("pending_manual", 0)
        automation_queued = counts.get("automation_queued", 0)
        submitted_manual = counts.get("submitted_manual", 0)
        applied = counts.get("applied", 0)
        phone_screens = counts.get("phone_screen", 0)
        technical_interviews = counts.get("technical", 0)
        offers = counts.get("offer", 0)
        rejections = counts.get("rejected", 0)

        # All applications that were submitted
        submitted_total = (
            submitted_manual
            + applied
            + phone_screens
            + technical_interviews
            + offers
            + rejections
        )

        positive_responses = phone_screens + technical_interviews + offers
        responses = rejections + positive_responses
        no_response = submitted_manual + applied

        response_rate = round(responses / submitted_total, 3) if submitted_total > 0 else 0.0
        positive_response_rate = round(positive_responses / submitted_total, 3) if submitted_total > 0 else 0.0
        offer_rate = round(offers / submitted_total, 3) if submitted_total > 0 else 0.0

        # Calculate average days to response
        response_deltas = []
        for app in applications:
            status = app.status if isinstance(app.status, str) else getattr(app.status, "value", str(app.status))
            if status in ("phone_screen", "technical", "offer", "rejected"):
                applied_at = getattr(app, "applied_at", None)
                updated_at = getattr(app, "updated_at", None)
                if applied_at and updated_at:
                    delta = (updated_at - applied_at).total_seconds() / 86400.0
                    if delta >= 0:
                        response_deltas.append(delta)

        avg_days = round(sum(response_deltas) / len(response_deltas), 1) if response_deltas else None

        return FunnelMetrics(
            total_applications=total,
            pending_manual=pending_manual,
            automation_queued=automation_queued,
            submitted_total=submitted_total,
            submitted_manual=submitted_manual,
            applied=applied,
            no_response=no_response,
            responses=responses,
            rejections=rejections,
            positive_responses=positive_responses,
            phone_screens=phone_screens,
            technical_interviews=technical_interviews,
            offers=offers,
            response_rate=response_rate,
            positive_response_rate=positive_response_rate,
            offer_rate=offer_rate,
            avg_days_to_response=avg_days,
        )
