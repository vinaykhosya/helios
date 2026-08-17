"""
tests/unit/integrations/google_sheets/test_sheets_sync.py

Unit tests for GoogleSheetsClient, GoogleSheetsSyncService, and column header mapping.
"""
import pytest
from unittest.mock import MagicMock, patch

from core.models.human_queue import HumanQueueEntry
from core.models.job import Job, JobSource, RemotePolicy
from integrations.google_sheets.client import (
    GoogleSheetsClient,
    MACHINE_HEADERS,
    DISPLAY_HEADERS,
)
from integrations.google_sheets.sync_service import GoogleSheetsSyncService


class MockWorksheet:
    """In-memory mock worksheet simulating Google Sheet grid with header name mapping."""

    def __init__(self, headers=None):
        self.rows = [
            list(headers or MACHINE_HEADERS),
            list(DISPLAY_HEADERS),
        ]

    def row_values(self, row_num: int) -> list[str]:
        if 1 <= row_num <= len(self.rows):
            return list(self.rows[row_num - 1])
        return []

    def col_values(self, col_num: int) -> list[str]:
        col_idx = col_num - 1
        res = []
        for r in self.rows:
            if col_idx < len(r):
                res.append(r[col_idx])
            else:
                res.append("")
        return res

    def append_row(self, row: list[str]) -> None:
        self.rows.append(list(row))

    def update_cell(self, row_num: int, col_num: int, val: str) -> None:
        while len(self.rows) < row_num:
            self.rows.append([])
        target_row = self.rows[row_num - 1]
        while len(target_row) < col_num:
            target_row.append("")
        target_row[col_num - 1] = str(val)


@pytest.fixture
def mock_sheets_client():
    ws = MockWorksheet()
    client = GoogleSheetsClient(spreadsheet_id="test-sheet-id")
    client._ws = ws
    client._client = MagicMock()
    return client, ws


def _make_sample_entry(entry_id="entry-001", app_id="app-001"):
    return HumanQueueEntry(
        id=entry_id,
        user_id="u1",
        job_id="j1",
        application_id=app_id,
        fit_score=0.92,
        confidence_score=0.95,
        friction_score=1,
        routing_reason="92% match",
        matching_skills=["Python", "FastAPI"],
        missing_skills=["Kubernetes"],
    )


def _make_sample_job():
    return Job(
        id="j1",
        source=JobSource.LEVER,
        source_id="lever-101",
        source_url="https://jobs.lever.co/acme/101",
        title="Staff Backend Engineer",
        company="Acme Corp",
        location="Remote",
        remote=RemotePolicy.REMOTE,
    )


def test_column_map_resolution(mock_sheets_client):
    client, ws = mock_sheets_client
    col_map = client.get_column_map()
    assert col_map["__helios_id"] == 1
    assert col_map["__helios_company"] == 2
    assert "__helios_mark_applied_url" in col_map


def test_push_row_new_entry(mock_sheets_client):
    client, ws = mock_sheets_client
    svc = GoogleSheetsSyncService(client)

    entry = _make_sample_entry()
    job = _make_sample_job()
    token = "test-fernet-token-xyz"

    success = svc.sync_entry(entry, job, mark_applied_token=token)
    assert success is True
    assert len(ws.rows) == 3   # 2 header rows + 1 data row

    row_data = ws.rows[2]
    col_map = client.get_column_map()

    assert row_data[col_map["__helios_id"] - 1] == "entry-001"
    assert row_data[col_map["__helios_company"] - 1] == "Acme Corp"
    assert row_data[col_map["__helios_role"] - 1] == "Staff Backend Engineer"
    assert row_data[col_map["__helios_match_score"] - 1] == "92%"
    assert "test-fernet-token-xyz" in row_data[col_map["__helios_mark_applied_url"] - 1]


def test_push_row_updates_existing_entry_without_creating_duplicate(mock_sheets_client):
    client, ws = mock_sheets_client
    svc = GoogleSheetsSyncService(client)

    entry = _make_sample_entry(entry_id="entry-dup-test")
    job = _make_sample_job()

    # First sync
    svc.sync_entry(entry, job, mark_applied_token="token-1")
    assert len(ws.rows) == 3

    # Second sync (e.g. status changed to approved)
    updated_entry = entry.transition_to("approved")
    svc.sync_entry(updated_entry, job, mark_applied_token="token-1")

    # MUST still be 3 rows total (no duplicate created)
    assert len(ws.rows) == 3
    col_map = client.get_column_map()
    assert ws.rows[2][col_map["__helios_status"] - 1] == "approved"


def test_sync_preserves_user_owned_columns(mock_sheets_client):
    """
    INVARIANT: Helios MUST NEVER overwrite user_* columns (e.g. user_notes, user_response).
    """
    client, ws = mock_sheets_client
    svc = GoogleSheetsSyncService(client)

    entry = _make_sample_entry(entry_id="entry-user-col")
    job = _make_sample_job()

    # 1. Initial push
    svc.sync_entry(entry, job, mark_applied_token="token-1")

    col_map = client.get_column_map()
    user_notes_col = col_map["user_notes"]

    # 2. User types notes in the sheet
    ws.update_cell(3, user_notes_col, "Had a screening call with recruiter on Tuesday")

    # 3. Helios re-syncs the row
    svc.sync_entry(entry, job, mark_applied_token="token-1")

    # 4. User notes MUST be intact!
    assert ws.rows[2][user_notes_col - 1] == "Had a screening call with recruiter on Tuesday"


def test_dynamic_reordered_and_inserted_columns_supported():
    """
    Test that if a user inserts custom columns or reorders columns in the sheet,
    Helios continues to write to the correct columns because it uses header-name mapping.
    """
    # Custom headers with inserted column and swapped order
    custom_headers = [
        "__helios_id",
        "custom_user_column_1",   # inserted between id and company
        "__helios_company",
        "__helios_role",
        "custom_priority_flag",   # inserted
        "__helios_match_score",
        "__helios_why",
        "__helios_matching_skills",
        "__helios_missing_skills",
        "__helios_location",
        "__helios_ats",
        "__helios_friction",
        "__helios_apply_url",
        "__helios_mark_applied_url",
        "__helios_resume",
        "__helios_status",
        "__helios_last_synced",
        "user_notes",
    ]

    ws = MockWorksheet(headers=custom_headers)
    client = GoogleSheetsClient(spreadsheet_id="test-reordered-sheet")
    client._ws = ws
    svc = GoogleSheetsSyncService(client)

    entry = _make_sample_entry(entry_id="entry-reorder")
    job = _make_sample_job()

    svc.sync_entry(entry, job, mark_applied_token="token-reorder")

    col_map = client.get_column_map()
    row_data = ws.rows[2]

    # Verify company is written to col 3 (its new position) and not col 2
    assert col_map["__helios_company"] == 3
    assert row_data[col_map["__helios_company"] - 1] == "Acme Corp"
    assert row_data[col_map["__helios_role"] - 1] == "Staff Backend Engineer"


def test_sync_fails_gracefully_when_client_errors():
    """
    INVARIANT #4: Sync failures must return False and NEVER raise or crash the caller.
    """
    failing_client = MagicMock()
    failing_client.push_row.side_effect = RuntimeError("Google API Rate Limit 429")

    svc = GoogleSheetsSyncService(failing_client)
    entry = _make_sample_entry()

    # Must NOT raise exception
    res = svc.sync_entry(entry)
    assert res is False
