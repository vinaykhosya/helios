"""
tests/test_session_manager.py

Unit tests for Helios Portal Session Manager.
"""
import os
import tempfile
import pytest
from unittest.mock import AsyncMock, MagicMock
from automation.sessions.manager import PortalSessionManager


@pytest.mark.asyncio
async def test_session_manager_save_and_retrieve():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PortalSessionManager(sessions_dir=tmpdir)

        # Mock Playwright context
        mock_context = AsyncMock()
        mock_context.storage_state = AsyncMock()

        # Save session
        state_file = await manager.save_session(mock_context, "siemens", auth_state="authenticated")
        assert os.path.exists(os.path.dirname(state_file))
        assert mock_context.storage_state.called

        # Create dummy storage file to simulate Playwright output
        with open(state_file, "w") as f:
            f.write('{"cookies": [], "origins": []}')

        # Check metadata
        meta = manager.get_session_metadata("siemens")
        assert meta is not None
        assert meta["portal"] == "siemens"
        assert meta["auth_state"] == "authenticated"

        # Check valid state path
        valid_path = manager.get_storage_state_path_if_valid("siemens")
        assert valid_path == state_file


@pytest.mark.asyncio
async def test_session_invalidation():
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = PortalSessionManager(sessions_dir=tmpdir)

        mock_context = AsyncMock()
        state_file = await manager.save_session(mock_context, "lever", auth_state="authenticated")
        with open(state_file, "w") as f:
            f.write('{"cookies": [], "origins": []}')

        # Invalidate session
        manager.invalidate_session("lever")

        meta = manager.get_session_metadata("lever")
        assert meta["auth_state"] == "expired"
        assert manager.get_storage_state_path_if_valid("lever") is None
