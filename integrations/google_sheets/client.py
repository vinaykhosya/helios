"""
integrations/google_sheets/client.py

GoogleSheetsClient — wraps gspread.
Column identity is by HEADER NAME, never by column letter or index.
Users can insert, delete, or move columns freely without breaking sync.

Sheet structure:
  Row 1: machine headers (__helios_* and user_*)
  Row 2: human display names (can be renamed freely by user)
  Row 3+: data rows

Column namespaces:
  __helios_*  — owned by Helios, overwritten on every sync
  user_*      — owned by the user, NEVER overwritten by Helios
"""
from __future__ import annotations

import json
import os
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials


SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

MACHINE_HEADERS = [
    "__helios_id",
    "__helios_company",
    "__helios_role",
    "__helios_match_score",
    "__helios_why",
    "__helios_matching_skills",
    "__helios_missing_skills",
    "__helios_location",
    "__helios_ats",
    "__helios_friction",
    "__helios_apply_url",
    "__helios_mark_applied_url",    # GET /mark-applied/{token}
    "__helios_resume",
    "__helios_status",
    "__helios_last_synced",
    "user_notes",
    "user_response",
    "user_interview",
]

DISPLAY_HEADERS = [
    "Helios ID", "Company", "Role", "Match %", "Why Recommended",
    "Your Skills", "Missing Skills", "Location", "ATS", "Friction",
    "Apply Here →", "✅ Mark Applied →",
    "Resume", "Status", "Last Synced",
    "Notes", "Response", "Interview",
]


class GoogleSheetsClient:

    def __init__(self, spreadsheet_id: str, worksheet_name: str = "Helios Queue"):
        self._spreadsheet_id = spreadsheet_id
        self._worksheet_name = worksheet_name
        self._client: Optional[gspread.Client] = None
        self._ws: Optional[gspread.Worksheet] = None

    def _get_client(self) -> gspread.Client:
        if self._client:
            return self._client
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not sa_json:
            raise EnvironmentError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
        creds = Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
        self._client = gspread.authorize(creds)
        return self._client

    def get_worksheet(self) -> gspread.Worksheet:
        if self._ws:
            return self._ws
        client = self._get_client()
        ss = client.open_by_key(self._spreadsheet_id)
        try:
            ws = ss.worksheet(self._worksheet_name)
        except gspread.WorksheetNotFound:
            ws = ss.add_worksheet(self._worksheet_name, rows=1000, cols=len(MACHINE_HEADERS))
            ws.append_row(MACHINE_HEADERS)
            ws.append_row(DISPLAY_HEADERS)
        self._ws = ws
        return ws

    def get_column_map(self) -> dict[str, int]:
        """
        Build {header_name: 1-based column index} from row 1.
        Called on every sync so column moves/inserts are handled automatically.
        Never hardcodes A/B/C column letters.
        """
        ws = self.get_worksheet()
        row1 = ws.row_values(1)
        return {name: idx + 1 for idx, name in enumerate(row1)}

    def find_row_by_helios_id(self, helios_id: str) -> Optional[int]:
        """Return 1-based row number of an existing entry, or None."""
        if not helios_id:
            return None
        ws = self.get_worksheet()
        col_map = self.get_column_map()
        id_col = col_map.get("__helios_id")
        if not id_col:
            return None
        col_values = ws.col_values(id_col)
        for idx, val in enumerate(col_values):
            if val == helios_id and idx >= 2:   # skip header rows (rows 1 & 2)
                return idx + 1
        return None

    def push_row(self, data: dict) -> None:
        """
        Write or update a row identified by __helios_id.
        Only writes __helios_* columns. Never touches user_* columns.
        """
        ws = self.get_worksheet()
        col_map = self.get_column_map()

        existing_row = self.find_row_by_helios_id(data.get("__helios_id", ""))

        if existing_row:
            # Update only __helios_* cells by header name
            for header, value in data.items():
                if not header.startswith("__helios_"):
                    continue   # INVARIANT: never write user_* columns
                col_idx = col_map.get(header)
                if col_idx:
                    ws.update_cell(existing_row, col_idx, value)
        else:
            # New row: write all columns in header order
            row = [""] * len(col_map)
            for header, value in data.items():
                col_idx = col_map.get(header)
                if col_idx:
                    row[col_idx - 1] = value
            ws.append_row(row)
