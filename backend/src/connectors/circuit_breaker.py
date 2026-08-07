"""
backend/src/connectors/circuit_breaker.py

CircuitBreaker state machine to protect remote connector API integrations.
"""
from __future__ import annotations

import time
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreaker:
    """
    Circuit Breaker pattern implementation.
    Trips after a configured failure threshold and cools down before probing in half-open state.
    """

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 300.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.last_state_change = time.time()

    def can_execute(self) -> bool:
        """Query if the circuit breaker permits the request invocation."""
        if self.state == CircuitState.CLOSED:
            return True
        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - self.last_state_change > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = time.time()
                return True
            return False
        # HALF_OPEN permits a trial request
        return True

    def record_success(self) -> None:
        """Record success: resets failures and closes the circuit."""
        self.consecutive_failures = 0
        if self.state != CircuitState.CLOSED:
            self.state = CircuitState.CLOSED
            self.last_state_change = time.time()

    def record_failure(self) -> None:
        """Record failure: increments consecutive failure counters and trips if threshold reached."""
        self.consecutive_failures += 1
        if self.state == CircuitState.CLOSED and self.consecutive_failures >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.state == CircuitState.HALF_OPEN:
            # Re-trip the circuit immediately on half-open failure
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
