"""
core/models/tailor.py

Domain models for asynchronous fact-constrained AI tailoring jobs.
Tracks lifecycle stages, truthfulness validation status, alignment metrics,
and compiled PDF / LaTeX artifacts.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class TailorJobStatus(str, Enum):
    QUEUED = "queued"
    EXTRACTING_FACTS = "extracting_facts"
    GENERATING = "generating"
    VALIDATING = "validating"
    COMPILING_PDF = "compiling_pdf"
    COMPLETED = "completed"
    REJECTED_VALIDATION = "rejected_validation"
    FAILED = "failed"


class AlignmentMetrics(BaseModel):
    matched_keywords_count: int = 0
    total_target_keywords: int = 0
    matched_keywords: List[str] = Field(default_factory=list)
    missing_keywords: List[str] = Field(default_factory=list)
    required_skills_count: int = 0
    total_required_skills: int = 0
    required_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    role_alignment_pct: int = 0


class TruthfulnessValidationReport(BaseModel):
    passed: bool = True
    no_fabricated_companies: bool = True
    no_fabricated_metrics: bool = True
    no_fabricated_degrees: bool = True
    no_fabricated_projects: bool = True
    violations: List[str] = Field(default_factory=list)
    verified_fact_count: int = 0


class TailorJob(BaseModel):
    id: str = Field(default_factory=lambda: f"tailor-{uuid.uuid4().hex[:8]}")
    job_id: str
    job_title: str
    company_name: str
    profile_id: str = "ai_ml"
    
    status: TailorJobStatus = TailorJobStatus.QUEUED
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    alignment: AlignmentMetrics = Field(default_factory=AlignmentMetrics)
    validation: TruthfulnessValidationReport = Field(default_factory=TruthfulnessValidationReport)
    
    original_latex: str = ""
    tailored_latex: str = ""
    cover_letter_text: str = ""
    pdf_path: Optional[str] = None
    error_message: Optional[str] = None
    
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    
    def add_log(self, stage: str, message: str) -> None:
        self.logs.append({
            "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
            "stage": stage,
            "message": message,
        })
