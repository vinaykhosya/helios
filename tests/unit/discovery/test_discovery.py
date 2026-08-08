"""
tests/unit/discovery/test_discovery.py

Unit tests for Helios v5.0 CareersDiscoveryEngine.
"""
import pytest
from unittest.mock import AsyncMock
from automation.discovery.careers_discovery import CareersDiscoveryEngine


@pytest.mark.asyncio
async def test_careers_discovery_engine_parsing():
    mock_page = AsyncMock()
    mock_page.goto = AsyncMock()
    mock_page.wait_for_timeout = AsyncMock()
    mock_page.title = AsyncMock(return_value="Siemens Careers")

    mock_search = AsyncMock()
    mock_search.is_visible = AsyncMock(return_value=True)
    mock_search.fill = AsyncMock()

    mock_link = AsyncMock()
    mock_link.get_attribute = AsyncMock(return_value="https://jobs.siemens.com/en_US/externaljobs/job/101")
    mock_link.inner_text = AsyncMock(return_value="Software Engineer")

    async def fake_query(sel):
        if "search" in sel:
            return mock_search
        return None

    mock_page.query_selector = AsyncMock(side_effect=fake_query)
    mock_page.query_selector_all = AsyncMock(return_value=[mock_link])

    discovered = await CareersDiscoveryEngine.discover_jobs(mock_page, "Siemens", "Software Engineer")

    assert len(discovered) == 1
    assert discovered[0].title == "Software Engineer"
    assert discovered[0].company == "Siemens"
    assert "siemens.com" in discovered[0].requisition_url
