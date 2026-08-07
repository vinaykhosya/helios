"""
core/interfaces/snapshot_store.py

SnapshotStore protocol and implementations (LocalSnapshotStore, DisabledSnapshotStore).
"""
from __future__ import annotations

import os
import json
import uuid
from datetime import datetime
from typing import Protocol


class SnapshotStore(Protocol):
    """Protocol for connector payload archival snapshots."""

    async def save(self, connector: str, source_id: str, payload: dict) -> None:
        """Save a raw payload snapshot for a connector job."""
        ...


class LocalSnapshotStore(SnapshotStore):
    """Local filesystem snapshot store. Preserves historical copies chronologically."""

    def __init__(self, base_dir: str = "connector_payloads"):
        self.base_dir = base_dir

    async def save(self, connector: str, source_id: str, payload: dict) -> None:
        try:
            # YYYY-MM-DDTHH-MM-SSZ format
            timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
            request_id = str(uuid.uuid4())[:8]

            dir_path = os.path.join(self.base_dir, connector)
            os.makedirs(dir_path, exist_ok=True)

            filename = f"{timestamp}_{connector}_{source_id}_{request_id}.json"
            file_path = os.path.join(dir_path, filename)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"LocalSnapshotStore failed to save snapshot for job {source_id}: {e}")


class DisabledSnapshotStore(SnapshotStore):
    """Disabled snapshot store for testing. No-op implementation."""

    async def save(self, connector: str, source_id: str, payload: dict) -> None:
        pass
