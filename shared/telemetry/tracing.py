"""
shared/telemetry/tracing.py

Telemetry tracing contracts.
Defines protocols for distributed trace propagation across workers and pipeline runs.
"""
from __future__ import annotations

from typing import Any, Generator, Protocol


class Tracer(Protocol):
    """Protocol for managing trace contexts across execution spans."""

    def start_span(self, name: str, correlation_id: str, parent_span_id: Optional[str] = None) -> TraceSpan:
        """Start a new logical execution span."""
        ...


class TraceSpan(Protocol):
    """Protocol for a single trace span context."""

    span_id: str
    parent_span_id: Optional[str]
    correlation_id: str

    def set_attribute(self, key: str, value: Any) -> None:
        """Add context metadata to the span."""
        ...

    def set_error(self, error: Exception) -> None:
        """Record an exception on the span."""
        ...

    def finish(self) -> None:
        """Mark the span as completed."""
        ...


# Allow Optional without importing typing at call sites
from typing import Optional  # noqa: E402
