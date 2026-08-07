"""
automation/replay.py

ReplayEngine — Re-executes failed application attempts using stored RecoverySnapshots.
Enables 1-click application replay for debugging and automated retry after selector or network fixes.
"""
from __future__ import annotations

import json
import os
from typing import Optional
from pydantic import BaseModel, Field

from automation.browser import BrowserSession
from automation.fillers.greenhouse import GreenhouseFormFiller
from automation.recovery import RecoverySnapshot
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job, JobSource


class ReplayResult(BaseModel):
    snapshot_id: str
    success: bool
    message: str
    replayed_at_timestamp: float


class ReplayEngine:
    """
    Reloads a failed application attempt from a RecoverySnapshot and retries form filling.
    """

    def __init__(self, greenhouse_filler: Optional[GreenhouseFormFiller] = None):
        self.filler = greenhouse_filler or GreenhouseFormFiller()

    async def replay_from_snapshot(
        self,
        snapshot: RecoverySnapshot,
        job: Job,
        candidate: CandidateProfile,
        resume_path: str,
    ) -> ReplayResult:
        """
        Re-executes application filling using stored snapshot metadata.
        """
        import time

        if not os.path.exists(snapshot.html_snapshot_path):
            return ReplayResult(
                snapshot_id=snapshot.snapshot_id,
                success=False,
                message=f"HTML snapshot file not found: {snapshot.html_snapshot_path}",
                replayed_at_timestamp=time.time(),
            )

        async with BrowserSession(headless=True) as page:
            try:
                # Fill form using target apply_url
                success = await self.filler.fill(page, job, candidate, resume_path)
                return ReplayResult(
                    snapshot_id=snapshot.snapshot_id,
                    success=success,
                    message="Replay succeeded",
                    replayed_at_timestamp=time.time(),
                )
            except Exception as e:
                return ReplayResult(
                    snapshot_id=snapshot.snapshot_id,
                    success=False,
                    message=f"Replay failed: {str(e)}",
                    replayed_at_timestamp=time.time(),
                )
