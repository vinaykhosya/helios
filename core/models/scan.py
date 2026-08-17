"""
core/models/scan.py

Domain models for asynchronous discovery scans.
Tracks per-portal scan status, job yield, durations, and real-time event logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field


class ScanStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PortalStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    WARNING = "warning"
    FAILED = "failed"


class PortalResult(BaseModel):
    name: str
    status: PortalStatus = PortalStatus.PENDING
    jobs_found: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None


class ScanJob(BaseModel):
    id: str = Field(default_factory=lambda: f"scan-{uuid.uuid4().hex[:8]}")
    status: ScanStatus = ScanStatus.QUEUED
    query: str = ""
    location: str = ""
    profile_id: str = "ai_ml"
    
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    portals: Dict[str, PortalResult] = Field(default_factory=lambda: {
        "ashby": PortalResult(name="Ashby"),
        "greenhouse": PortalResult(name="Greenhouse"),
        "lever": PortalResult(name="Lever"),
        "linkedin": PortalResult(name="LinkedIn"),
        "workday": PortalResult(name="Workday"),
    })
    
    discovered_count: int = 0
    qualified_count: int = 0
    strong_count: int = 0
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    
    def add_log(self, level: str, portal: str, message: str) -> None:
        self.logs.append({
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            "level": level,
            "portal": portal,
            "message": message,
        })
