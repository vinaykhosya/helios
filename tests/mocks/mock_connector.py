"""
tests/mocks/mock_connector.py

In-memory BaseConnector implementation for unit and integration tests.
Returns a hardcoded list of Job objects. No HTTP calls.

Usage:
    from tests.mocks.mock_connector import MockConnector

    connector = MockConnector(jobs=[full_job])
    results = await connector.search("engineer")
    assert results[0].title == full_job.title
"""
from __future__ import annotations

from typing import Optional
from core.interfaces.connector import BaseConnector
from core.models.job import Job, JobSource


class MockConnector(BaseConnector):
    """
    Deterministic connector for testing.
    Returns a pre-configured list of jobs regardless of search parameters.
    """

    name = "mock"
    source_url = "https://mock.helios.test"

    def __init__(self, jobs: Optional[list[Job]] = None, healthy: bool = True):
        self._jobs = jobs or []
        self._healthy = healthy

    async def search(self, query: str, location: Optional[str] = None, max_results: int = 50, **kwargs) -> list[Job]:
        return self._jobs[:max_results]

    async def fetch(self, source_id: str) -> Job:
        for job in self._jobs:
            if job.source_id == source_id:
                return job
        from core.exceptions import JobNotFoundError
        raise JobNotFoundError(f"Mock job not found: {source_id}")

    def normalize(self, raw: dict) -> Job:
        return Job(
            source=JobSource.MANUAL,
            source_id=raw.get("id", "mock-id"),
            source_url=raw.get("url", "https://mock.helios.test/job/1"),
            title=raw.get("title", "Mock Job"),
            company=raw.get("company", "Mock Co"),
        )

    async def health_check(self) -> bool:
        return self._healthy
