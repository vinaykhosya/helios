"""
tests/unit/intelligence/test_selectors.py

Unit tests for SelectorResolver and 8-Priority Selector Hierarchy.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from automation.intelligence.contracts import ElementSemantic
from automation.intelligence.selectors import SelectorResolver


@pytest.mark.asyncio
async def test_selector_resolver_priority_1_autocomplete():
    mock_page = AsyncMock()
    mock_elem = MagicMock()
    mock_elem.is_visible = AsyncMock(return_value=True)
    
    # Query selector returns mock_elem when selector matches autocomplete='email'
    async def fake_query(sel):
        if "autocomplete='email'" in sel:
            return mock_elem
        return None

    mock_page.query_selector = AsyncMock(side_effect=fake_query)

    res = await SelectorResolver.locate_element(mock_page, ElementSemantic.EMAIL)
    assert res is not None
    elem, sel, conf = res
    assert elem == mock_elem
    assert "autocomplete='email'" in sel
    assert conf == 0.99


@pytest.mark.asyncio
async def test_selector_resolver_priority_3_ats_vendor_id():
    mock_page = AsyncMock()
    mock_elem = MagicMock()
    mock_elem.is_visible = AsyncMock(return_value=True)

    async def fake_query(sel):
        if "data-automation-id*='first_name'" in sel:
            return mock_elem
        return None

    mock_page.query_selector = AsyncMock(side_effect=fake_query)

    res = await SelectorResolver.locate_element(mock_page, ElementSemantic.FIRST_NAME)
    assert res is not None
    elem, sel, conf = res
    assert elem == mock_elem
    assert "data-automation-id" in sel
    assert conf == 0.97


@pytest.mark.asyncio
async def test_selector_resolver_unresolvable_returns_none():
    mock_page = AsyncMock()
    mock_page.query_selector = AsyncMock(return_value=None)

    res = await SelectorResolver.locate_element(mock_page, ElementSemantic.PHONE)
    assert res is None
