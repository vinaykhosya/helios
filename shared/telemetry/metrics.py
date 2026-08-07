"""
shared/telemetry/metrics.py

Telemetry metrics contracts.
Defines interfaces for collecting timing, counter, and cost metrics across Helios.
"""
from __future__ import annotations

from typing import Protocol


class MetricsCollector(Protocol):
    """Protocol for recording operational and AI cost metrics."""

    def increment(self, name: str, value: int = 1, tags: Optional[dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        ...

    def timing(self, name: str, value_ms: float, tags: Optional[dict[str, str]] = None) -> None:
        """Record a latency / duration metric in milliseconds."""
        ...

    def gauge(self, name: str, value: float, tags: Optional[dict[str, str]] = None) -> None:
        """Record an absolute gauge value."""
        ...

    def record_ai_cost(
        self,
        engine: str,
        provider: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
        latency_ms: float,
    ) -> None:
        """Track LLM token usage, cost, and latency."""
        ...


# Allow Optional without importing typing at call sites
from typing import Optional  # noqa: E402
from datetime import datetime
from pydantic import BaseModel, Field


class HeliosSessionMetrics(BaseModel):
    """
    Tracks cycle and daily metrics for morning briefing reports and dashboard analytics.
    """
    session_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    jobs_scanned: int = 0
    jobs_eligible: int = 0
    excellent_matches: int = 0

    applied: int = 0
    auto_applied: int = 0
    awaiting_approval: int = 0
    paused_captcha: int = 0
    failed: int = 0

    rejection_reasons: dict[str, int] = Field(default_factory=dict)
    avg_application_time_seconds: float = 0.0

