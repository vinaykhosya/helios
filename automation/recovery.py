"""
automation/recovery.py

RecoveryEngine — Form automation fault tolerance, DOM snapshot recorder, and error diagnostics.
Saves HTML snapshots, screenshots, and context to disk on form filling errors.
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional
from pydantic import BaseModel, Field


class RecoverySnapshot(BaseModel):
    snapshot_id: str
    job_id: str
    source: str
    apply_url: str
    error_message: str
    timestamp: float = Field(default_factory=time.time)
    html_snapshot_path: str
    metadata_path: str


class RecoveryEngine:
    """
    Captures DOM state and metadata when Playwright browser automation fails.
    """

    def __init__(self, snapshot_dir: Optional[str] = None):
        if snapshot_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            snapshot_dir = os.path.join(base_dir, "output", "recovery_snapshots")
        self.snapshot_dir = snapshot_dir
        os.makedirs(self.snapshot_dir, exist_ok=True)

    async def capture_failure(
        self,
        page: object,
        job_id: str,
        source: str,
        apply_url: str,
        error: Exception,
    ) -> RecoverySnapshot:
        """
        Captures DOM HTML, URL context, and exception details.
        """
        snapshot_id = f"{job_id}_{int(time.time())}"
        html_path = os.path.join(self.snapshot_dir, f"{snapshot_id}.html")
        meta_path = os.path.join(self.snapshot_dir, f"{snapshot_id}.json")

        # Capture HTML from Playwright page if method available
        html_content = ""
        try:
            if hasattr(page, "content"):
                html_content = await page.content()
        except Exception:
            html_content = "<!-- Failed to capture page content -->"

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        meta_data = {
            "snapshot_id": snapshot_id,
            "job_id": job_id,
            "source": source,
            "apply_url": apply_url,
            "error_message": str(error),
            "timestamp": time.time(),
            "html_snapshot_path": html_path,
        }

        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta_data, f, indent=2)

        return RecoverySnapshot(
            snapshot_id=snapshot_id,
            job_id=job_id,
            source=source,
            apply_url=apply_url,
            error_message=str(error),
            timestamp=meta_data["timestamp"],
            html_snapshot_path=html_path,
            metadata_path=meta_path,
        )
