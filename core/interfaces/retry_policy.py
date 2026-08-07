"""
core/interfaces/retry_policy.py

RetryPolicy protocol and implementations (ExponentialBackoffPolicy, NoRetryPolicy).
"""
from __future__ import annotations

import httpx
import asyncio
from typing import Protocol


class RetryPolicy(Protocol):
    """Protocol for classifying retryable vs non-retryable connector errors."""

    def should_retry(self, error: Exception) -> bool:
        """Evaluate if the caught exception is transient and should be retried."""
        ...

    def get_backoff(self, attempt: int) -> float:
        """Calculate sleep delay for exponential backoff."""
        ...


class ExponentialBackoffPolicy(RetryPolicy):
    """
    Standard Exponential Backoff Policy.
    Classifies timeouts, rate limits (429), and temporary server faults (5xx) as retryable.
    """

    def __init__(self, base_delay: float = 2.0, max_delay: float = 10.0):
        self.base_delay = base_delay
        self.max_delay = max_delay

    def should_retry(self, error: Exception) -> bool:
        # 1. Native timeouts
        if isinstance(error, (TimeoutError, asyncio.TimeoutError)):
            return True

        # 2. HTTPX specific network errors / timeouts
        if isinstance(error, (httpx.TimeoutException, httpx.NetworkError)):
            return True

        # 3. HTTP status response checking
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            # Retry on rate limiting (429) or internal server faults (5xx)
            if status_code == 429 or (status_code >= 500 and status_code < 600):
                return True

        return False

    def get_backoff(self, attempt: int) -> float:
        delay = self.base_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)


class NoRetryPolicy(RetryPolicy):
    """No Retry Policy. Aborts execution immediately on any error."""

    def should_retry(self, error: Exception) -> bool:
        return False

    def get_backoff(self, attempt: int) -> float:
        return 0.0
