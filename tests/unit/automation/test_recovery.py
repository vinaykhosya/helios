"""
tests/unit/automation/test_recovery.py

Unit tests for RecoveryEngine snapshot capture and error logging.
"""
import os
import pytest
from unittest.mock import AsyncMock
from automation.recovery import RecoveryEngine


@pytest.mark.asyncio
async def test_recovery_engine_capture_failure(tmp_path):
    engine = RecoveryEngine(snapshot_dir=str(tmp_path))

    mock_page = AsyncMock()
    mock_page.content.return_value = "<html><body><form>Broken form</form></body></html>"

    snapshot = await engine.capture_failure(
        page=mock_page,
        job_id="job_999",
        source="greenhouse",
        apply_url="https://boards.greenhouse.io/test/999",
        error=ValueError("Selector #first_name not found"),
    )

    assert os.path.exists(snapshot.html_snapshot_path)
    assert os.path.exists(snapshot.metadata_path)

    with open(snapshot.html_snapshot_path, "r", encoding="utf-8") as f:
        html = f.read()
    assert "Broken form" in html
