"""
automation/fillers/lever.py

LeverFormFiller — Playwright form filler for Lever job boards (jobs.lever.co).
Fills candidate full name, email, phone, org, LinkedIn URL, and uploads resume PDF.
"""
from __future__ import annotations

from typing import Optional
from ai.memory.service import MemoryService
from automation.fillers.greenhouse import PauseRequired
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job


class LeverFormFiller:
    """
    Automates Lever job application submission.
    """

    def __init__(self, memory_service: Optional[MemoryService] = None):
        self.memory = memory_service or MemoryService()

    async def fill(
        self,
        page: object,
        job: Job,
        candidate: CandidateProfile,
        resume_path: str,
        cover_letter_path: Optional[str] = None,
    ) -> bool:
        """
        Navigates to Lever application form and fills inputs.
        """
        apply_url = job.apply_url or job.source_url
        if not apply_url:
            raise ValueError(f"Job {job.id} has no apply_url")

        await page.goto(apply_url)

        # 1. CAPTCHA Check
        if await self._detect_captcha(page):
            raise PauseRequired(reason="CAPTCHA_DETECTED")

        # 2. Standard Lever Fields
        await self._fill_first_matching_selector(page, ["input[name='name']", "#name"], candidate.name)
        await self._fill_first_matching_selector(page, ["input[name='email']", "#email"], candidate.email)
        if candidate.phone:
            await self._fill_first_matching_selector(page, ["input[name='phone']", "#phone"], candidate.phone)
        if candidate.linkedin_url:
            await self._fill_first_matching_selector(page, ["input[name='urls[LinkedIn]']", "input[name*='linkedin']"], candidate.linkedin_url)

        # 3. Resume Upload
        if resume_path:
            await page.set_input_files("input[type='file'][name='resume'], #resume-upload-input", resume_path)

        return True

    async def _fill_first_matching_selector(self, page: object, selectors: list[str], value: str) -> bool:
        for sel in selectors:
            try:
                await page.fill(sel, value)
                return True
            except Exception:
                continue
        return False

    async def _detect_captcha(self, page: object) -> bool:
        captcha_selectors = ["iframe[src*='recaptcha']", "iframe[src*='hcaptcha']", ".g-recaptcha"]
        for sel in captcha_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    return True
            except Exception:
                continue
        return False
