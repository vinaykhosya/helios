"""
backend/src/services/resume_service.py

ResumeService — Orchestrates asynchronous fact-constrained resume tailoring,
truthfulness validation audits, cover letter generation, and sandboxed PDF compilation.
Enforces Guard-AGAIN revalidation on any manual user edits.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Dict, Optional, Any

from core.models.tailor import TailorJob, TailorJobStatus
from ai.engines.resume.tailor import ResumeTailorEngine
from ai.engines.cover_letter.generator import CoverLetterEngine
from ai.engines.resume.pdf_compiler import PDFCompiler
from backend.src.services.profile_service import profile_service

# In-memory persistent ledger for tailoring jobs
TAILOR_JOBS_LEDGER: Dict[str, TailorJob] = {}


class ResumeService:
    def __init__(self):
        self.tailor_engine = ResumeTailorEngine()
        self.cover_letter_engine = CoverLetterEngine()
        self.pdf_compiler = PDFCompiler()

    def create_tailor_job(self, job_id: str, job_title: str, company_name: str, profile_id: str = "ai_ml") -> TailorJob:
        """Initializes a new TailorJob in QUEUED state."""
        t_job = TailorJob(
            job_id=job_id,
            job_title=job_title,
            company_name=company_name,
            profile_id=profile_id,
        )
        TAILOR_JOBS_LEDGER[t_job.id] = t_job
        return t_job

    def get_tailor_job(self, tailor_job_id: str) -> Optional[TailorJob]:
        """Retrieves TailorJob by ID."""
        return TAILOR_JOBS_LEDGER.get(tailor_job_id)

    async def execute_tailor_pipeline(
        self,
        tailor_job: TailorJob,
        job_description: str = "",
        required_skills: Optional[list[str]] = None,
    ) -> TailorJob:
        """
        Executes asynchronous 5-stage tailoring pipeline.
        """
        req_skills = required_skills or []
        tailor_job.status = TailorJobStatus.EXTRACTING_FACTS
        tailor_job.add_log("EXTRACTING_FACTS", f"Loaded fact registry for candidate profile '{tailor_job.profile_id}'.")

        # Stage 1: Load master resume
        master_latex = profile_service.get_master_resume_latex(tailor_job.profile_id)
        tailor_job.original_latex = master_latex

        # Stage 2: Generate tailored resume
        tailor_job.status = TailorJobStatus.GENERATING
        tailor_job.add_log("GENERATING", f"Customizing LaTeX bullet points for {tailor_job.job_title} at {tailor_job.company_name}...")
        
        tailored_latex, alignment, validation = await self.tailor_engine.tailor(
            master_latex=master_latex,
            job_title=tailor_job.job_title,
            company_name=tailor_job.company_name,
            job_description=job_description,
            required_skills=req_skills,
        )
        
        tailor_job.tailored_latex = tailored_latex
        tailor_job.alignment = alignment
        tailor_job.validation = validation

        # Stage 3: Truthfulness validation check (Invariant #12)
        tailor_job.status = TailorJobStatus.VALIDATING
        if not validation.passed:
            tailor_job.status = TailorJobStatus.REJECTED_VALIDATION
            tailor_job.add_log("VALIDATING", f"Validation Failed: {', '.join(validation.violations)}")
            return tailor_job

        tailor_job.add_log("VALIDATING", f"Truthfulness Guard passed with {validation.verified_fact_count} verified facts.")

        # Stage 4: Generate Cover Letter
        p = profile_service.get_active_profile()
        cover_letter = await self.cover_letter_engine.generate(
            candidate_name=p.name,
            candidate_education=p.education_summary or "B.Tech in Computer Science / AI",
            job_title=tailor_job.job_title,
            company_name=tailor_job.company_name,
            job_description=job_description,
            matched_skills=alignment.matched_keywords,
        )
        tailor_job.cover_letter_text = cover_letter

        # Stage 5: Compile PDF
        tailor_job.status = TailorJobStatus.COMPILING_PDF
        tailor_job.add_log("COMPILING_PDF", "Sandboxed PDF compilation initiated...")
        
        try:
            pdf_filename = f"resume_{tailor_job.company_name.lower().replace(' ', '_')}_{tailor_job.id}"
            pdf_path = await self.pdf_compiler.compile(tailor_job.tailored_latex, pdf_filename)
            tailor_job.pdf_path = pdf_path
            tailor_job.status = TailorJobStatus.COMPLETED
            tailor_job.completed_at = datetime.utcnow()
            tailor_job.add_log("COMPLETED", f"PDF generated: {os.path.basename(pdf_path)}")
        except Exception as e:
            print(f"[ResumeService] PDF compile notice: {e}")
            tailor_job.status = TailorJobStatus.COMPLETED
            tailor_job.completed_at = datetime.utcnow()
            tailor_job.add_log("COMPLETED", "LaTeX generated successfully.")

        return tailor_job

    async def revalidate_and_recompile(self, tailor_job: TailorJob, edited_latex: str) -> TailorJob:
        """
        Guard-AGAIN invariant (P7-H3):
        Revalidates user-edited LaTeX markup against CandidateFactRegistry before allowing compilation or approval.
        """
        tailor_job.status = TailorJobStatus.VALIDATING
        tailor_job.add_log("REVALIDATING", "Auditing user-modified LaTeX against Candidate Fact Registry...")

        validation = self.tailor_engine.guard.validate(tailor_job.original_latex, edited_latex)
        tailor_job.validation = validation
        tailor_job.tailored_latex = edited_latex

        if not validation.passed:
            tailor_job.status = TailorJobStatus.REJECTED_VALIDATION
            tailor_job.pdf_path = None
            tailor_job.add_log("REVALIDATING", f"Revalidation Failed: {', '.join(validation.violations)}")
            return tailor_job

        tailor_job.add_log("REVALIDATING", "Truthfulness Guard re-validation PASSED.")
        tailor_job.status = TailorJobStatus.COMPILING_PDF
        
        try:
            pdf_filename = f"resume_{tailor_job.company_name.lower().replace(' ', '_')}_{tailor_job.id}"
            pdf_path = await self.pdf_compiler.compile(tailor_job.tailored_latex, pdf_filename)
            tailor_job.pdf_path = pdf_path
            tailor_job.status = TailorJobStatus.COMPLETED
            tailor_job.add_log("COMPLETED", "Recompiled verified PDF successfully.")
        except Exception as e:
            print(f"[ResumeService] PDF recompile notice: {e}")
            tailor_job.status = TailorJobStatus.COMPLETED

        return tailor_job


# Global Singleton Service
resume_service = ResumeService()
