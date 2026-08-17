"""
tests/unit/connectors/test_ashby_connector.py

Unit tests for AshbyConnector.
All network calls are mocked with httpx.MockTransport -- no real HTTP.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from backend.src.connectors.ashby import AshbyConnector, AshbyNormalizer
from core.models.job import Job, JobSource


def _fake_posting(id="abc123", title="Software Engineer", location="Remote") -> dict:
    return {
        "id": id,
        "title": title,
        "location": location,
        "jobUrl": f"https://jobs.ashbyhq.com/linear/{id}",
        "applyUrl": f"https://jobs.ashbyhq.com/linear/{id}/application",
        "descriptionSafe": "<p>We are building the future of project management.</p>",
        "companyName": "Linear",
    }


def _make_client_with_postings(postings: list[dict]) -> httpx.AsyncClient:
    """Returns a mock AsyncClient that returns the given postings."""
    payload = json.dumps({"jobs": postings}).encode()
    dummy_request = httpx.Request("GET", "https://api.ashbyhq.com/posting-api/job-board/linear")

    async def _mock_get(url, **kwargs):
        return httpx.Response(200, content=payload, request=dummy_request)

    client = MagicMock(spec=httpx.AsyncClient)
    client.get = _mock_get
    return client


@pytest.mark.asyncio
async def test_ashby_connector_search_returns_jobs():
    """
    AshbyConnector.search() returns Job objects from the API response.
    """
    connector = AshbyConnector(site="linear")
    connector.client = _make_client_with_postings([
        _fake_posting("j1", "Software Engineer"),
        _fake_posting("j2", "Product Manager"),
    ])

    jobs = await connector.search(query="")
    assert len(jobs) == 2
    assert all(isinstance(j, Job) for j in jobs)
    assert all(j.source == JobSource.ASHBY for j in jobs)


@pytest.mark.asyncio
async def test_ashby_connector_search_filters_by_query():
    """
    search(query="Engineer") returns only postings whose title matches the query.
    """
    connector = AshbyConnector(site="linear")
    connector.client = _make_client_with_postings([
        _fake_posting("j1", "Software Engineer"),
        _fake_posting("j2", "Product Manager"),
        _fake_posting("j3", "Data Engineer"),
    ])

    jobs = await connector.search(query="Engineer")
    titles = [j.title for j in jobs]
    assert len(jobs) == 2
    assert all("Engineer" in t for t in titles)


@pytest.mark.asyncio
async def test_ashby_connector_returns_empty_on_404():
    """AshbyConnector.search() returns [] when the company slug doesn't exist (404)."""
    dummy_request = httpx.Request("GET", "https://api.ashbyhq.com/posting-api/job-board/nonexistent")

    async def _mock_get_404(url, **kwargs):
        return httpx.Response(404, content=b"Not Found", request=dummy_request)

    connector = AshbyConnector(site="nonexistent-slug")
    connector.client = MagicMock(spec=httpx.AsyncClient)
    connector.client.get = _mock_get_404

    jobs = await connector.search()
    assert jobs == []


def test_ashby_normalizer_produces_valid_job():
    """AshbyNormalizer.normalize() produces a valid Job with correct source."""
    posting = _fake_posting("xyz", "Staff Engineer", "San Francisco, CA")
    job = AshbyNormalizer.normalize(posting, "linear")

    assert job.source == JobSource.ASHBY
    assert job.source_id == "xyz"
    assert job.title == "Staff Engineer"
    assert job.company == "Linear"
    assert job.location == "San Francisco, CA"
    assert job.source_url != ""
    assert job.apply_url != ""
