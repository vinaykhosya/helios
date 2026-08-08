"""
tests/unit/intelligence/test_submit_detector.py

Unit and regression tests for SubmitControlDetector.
Verifies multi-attribute submit control detection, wizard button exclusion,
and diagnostic classification for missing controls.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from automation.intelligence.submit_detector import SubmitControlDetector, SubmitCandidate, SubmitScanResult


@pytest.mark.asyncio
async def test_submit_detector_exact_text_match():
    page = AsyncMock()
    page.main_frame = page
    page.frames = [page]

    mock_btn = AsyncMock()
    mock_btn.is_visible = AsyncMock(return_value=True)
    mock_btn.inner_text = AsyncMock(return_value="Submit Application")
    mock_btn.get_attribute = AsyncMock(side_effect=lambda attr: {
        "value": None,
        "type": "submit",
        "role": "button",
        "disabled": None,
        "aria-disabled": "false",
        "data-automation-id": "submit-btn"
    }.get(attr))
    mock_btn.bounding_box = AsyncMock(return_value={"x": 100, "y": 500, "width": 120, "height": 40})

    page.query_selector_all = AsyncMock(return_value=[mock_btn])

    res = await SubmitControlDetector.scan_page(page)

    assert res.found is True
    assert res.best_candidate is not None
    assert res.best_candidate.text == "Submit Application"
    assert res.best_candidate.confidence >= 0.80
    assert res.best_candidate.enabled is True


@pytest.mark.asyncio
async def test_submit_detector_nvidia_apply_now_modal_flow():
    page = AsyncMock()
    page.main_frame = page
    page.frames = [page]

    apply_btn = AsyncMock()
    apply_btn.is_visible = AsyncMock(return_value=True)
    apply_btn.inner_text = AsyncMock(return_value="Apply Now")
    apply_btn.get_attribute = AsyncMock(side_effect=lambda attr: {
        "type": "button",
        "role": "button"
    }.get(attr))
    apply_btn.bounding_box = AsyncMock(return_value={"x": 24, "y": 390, "width": 150, "height": 44})

    cont_btn = AsyncMock()
    cont_btn.is_visible = AsyncMock(return_value=True)
    cont_btn.inner_text = AsyncMock(return_value="Continue")
    cont_btn.get_attribute = AsyncMock(side_effect=lambda attr: None)

    page.query_selector_all = AsyncMock(return_value=[apply_btn, cont_btn])

    res = await SubmitControlDetector.scan_page(page)

    assert res.found is True
    assert res.best_candidate is not None
    assert res.best_candidate.text == "Apply Now"
    assert res.best_candidate.confidence >= 0.60


@pytest.mark.asyncio
async def test_submit_detector_wizard_next_excluded():
    page = AsyncMock()
    page.main_frame = page
    page.frames = [page]

    next_btn = AsyncMock()
    next_btn.is_visible = AsyncMock(return_value=True)
    next_btn.inner_text = AsyncMock(return_value="Next")
    next_btn.get_attribute = AsyncMock(return_value=None)

    page.query_selector_all = AsyncMock(return_value=[next_btn])
    page.inner_text = AsyncMock(return_value="Wizard Step 1")
    page.title = AsyncMock(return_value="Application")
    page.query_selector = AsyncMock(return_value=next_btn)

    res = await SubmitControlDetector.scan_page(page)

    assert res.found is False
    assert res.diagnostic_reason == "APPLICATION_IN_WIZARD_STEP_NOT_FINAL_REVIEW"
