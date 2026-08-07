"""
tests/unit/backend/connectors/test_greenhouse.py

Unit tests for GreenhouseConnector.
Mocks the httpx.AsyncClient response to test search, fetch, and normalize.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from backend.src.connectors.greenhouse import GreenhouseConnector, GreenhouseJob
from core.models.job import JobSource


@pytest.mark.asyncio
async def test_greenhouse_normalize():
    connector = GreenhouseConnector(board_token="google")
    raw_data = {
        "id": 12345,
        "title": "Systems Architect",
        "absolute_url": "https://google.com/careers/12345",
        "location": {"name": "Munich, Germany"},
        "content": "<p>Description HTML</p>",
    }

    job = connector.normalize(raw_data)
    assert job.source == JobSource.GREENHOUSE
    assert job.source_id == "12345"
    assert job.title == "Systems Architect"
    assert job.company == "Google"
    assert job.location == "Munich, Germany"
    assert job.description == "<p>Description HTML</p>"


@pytest.mark.asyncio
async def test_greenhouse_search_mocked():
    connector = GreenhouseConnector(board_token="acme")

    # Mock the internal client's GET method
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "jobs": [
            {
                "id": 101,
                "title": "Software Developer",
                "location": {"name": "Remote"},
                "content": "Nice job",
            },
            {
                "id": 102,
                "title": "Product Owner",
                "location": {"name": "New York"},
                "content": "Cool job",
            },
        ]
    }

    connector.client.get = AsyncMock(return_value=mock_response)

    # Search for "Software"
    jobs = await connector.search(query="Software")
    assert len(jobs) == 1
    assert jobs[0].source_id == "101"
    assert jobs[0].title == "Software Developer"


@pytest.mark.asyncio
async def test_greenhouse_fetch_mocked():
    connector = GreenhouseConnector(board_token="acme")

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "id": 202,
        "title": "Lead designer",
        "location": {"name": "London"},
        "content": "Design stuff",
    }

    connector.client.get = AsyncMock(return_value=mock_response)

    job = await connector.fetch("202")
    assert job.source_id == "202"
    assert job.title == "Lead designer"
    assert job.location == "London"
