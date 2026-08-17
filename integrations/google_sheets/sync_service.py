"""
integrations/google_sheets/sync_service.py

GoogleSheetsSyncService — pushes Human Queue entries to Google Sheets.

V1 design (PUSH-ONLY):
  - Helios writes __helios_* columns only
  - Users write user_* columns (notes, response, interview stage)
  - Helios NEVER reads user_* columns back
  - The Mark Applied link is a GET URL containing a signed token
  - Bidirectional sync is NOT implemented in V1
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.models.human_queue import HumanQueueEntry
from core.models.job import Job
from integrations.google_sheets.client import GoogleSheetsClient


class GoogleSheetsSyncService:

    def __init__(self, sheets_client: GoogleSheetsClient):
        self._client = sheets_client

    def sync_entry(
        self,
        entry: HumanQueueEntry,
        job: Optional[Job] = None,
        mark_applied_token: str = "",
        helios_base_url: str = "https://helios.vinaykhosya.com",
    ) -> bool:
        """
        Push one Human Queue entry to the Sheet.
        Returns True on success, False on any error (sync failure never blocks pipeline).
        mark_applied_token: Fernet-signed token from ActionTokenService.
                            Builds /mark-applied/{token} URL embedded in the sheet.
        """
        try:
            row_data = self._entry_to_row(entry, job, mark_applied_token, helios_base_url)
            self._client.push_row(row_data)
            return True
        except Exception as e:
            print(f"[GoogleSheets] Sync failed for entry {entry.id}: {e}")
            return False

    def _entry_to_row(
        self,
        entry: HumanQueueEntry,
        job: Optional[Job] = None,
        mark_applied_token: str = "",
        helios_base_url: str = "https://helios.vinaykhosya.com",
    ) -> dict:
        """
        Build {machine_header: value} for one sheet row.
        Only __helios_* keys are included. user_* columns are intentionally omitted.
        """
        friction_labels = {0: "STANDARD", 1: "MODERATE", 2: "HEAVY", 3: "BLOCKING"}

        mark_applied_url = (
            f"{helios_base_url}/mark-applied/{mark_applied_token}"
            if mark_applied_token else ""
        )

        ats_name = ""
        if job and hasattr(job, "source"):
            ats_name = job.source.value if hasattr(job.source, "value") else str(job.source)

        return {
            "__helios_id":               entry.id,
            "__helios_company":          job.company if job else "",
            "__helios_role":             job.title if job else "",
            "__helios_match_score":      f"{int((entry.fit_score or 0) * 100)}%",
            "__helios_why":              entry.routing_reason or "",
            "__helios_matching_skills":  ", ".join(entry.matching_skills[:5]),
            "__helios_missing_skills":   ", ".join(entry.missing_skills[:5]),
            "__helios_location":         getattr(job, "location", "") or "",
            "__helios_ats":              ats_name,
            "__helios_friction":         friction_labels.get(entry.friction_score, "?"),
            "__helios_apply_url":        entry.application_url or "",
            "__helios_mark_applied_url": mark_applied_url,
            "__helios_resume":           entry.resume_path or "master_resume.pdf",
            "__helios_status":           entry.decision,
            "__helios_last_synced":      datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        }
