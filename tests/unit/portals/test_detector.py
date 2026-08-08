"""
tests/unit/portals/test_detector.py

Unit tests for PortalDetector emitting PortalIdentity contracts.
"""
import pytest
from unittest.mock import AsyncMock
from automation.portals.detector import PortalDetector


@pytest.mark.asyncio
async def test_portal_detector_lever():
    mock_page = AsyncMock()
    mock_page.url = "https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5"

    identity = await PortalDetector.detect(mock_page)
    assert identity.type == "lever"
    assert identity.company == "cred"
    assert identity.confidence == 0.99


@pytest.mark.asyncio
async def test_portal_detector_workday():
    mock_page = AsyncMock()
    mock_page.url = "https://siemens.wd3.myworkdayjobs.com/Siemens_Careers"

    identity = await PortalDetector.detect(mock_page)
    assert identity.type == "workday"
    assert identity.company == "siemens"
    assert identity.confidence == 0.99


@pytest.mark.asyncio
async def test_portal_detector_generic():
    mock_page = AsyncMock()
    mock_page.url = "https://careers.acmecompany.com/jobs/123"

    identity = await PortalDetector.detect(mock_page)
    assert identity.type == "generic"
    assert identity.company == "acmecompany"
    assert identity.confidence == 0.80
