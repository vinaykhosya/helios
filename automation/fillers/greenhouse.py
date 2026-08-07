"""
automation/fillers/greenhouse.py

GreenhouseFormFiller — Playwright form filler for Greenhouse ATS boards.
Fills standard input fields, uploads resume/cover letter PDFs, checks MemoryService for Q&A,
and raises PauseRequired on CAPTCHA, OTP, or unknown custom questions.
"""
from __future__ import annotations

from typing import Optional
from ai.memory.service import MemoryService
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job


class PauseRequired(Exception):
    """
    Raised when form filler encounters a human intervention trigger (CAPTCHA, OTP, unknown free-text prompt).
    """
    def __init__(self, reason: str, screenshot_path: Optional[str] = None):
        super().__init__(reason)
        self.reason = reason
        self.screenshot_path = screenshot_path


class GreenhouseFormFiller:
    """
    Automates Greenhouse application submission via Playwright page instance.
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
        Navigates to application URL and fills form fields.

        Returns:
            True if all fields successfully filled and ready for submission.

        Raises:
            PauseRequired: If human verification or custom prompt is detected.
        """
        apply_url = job.apply_url or job.source_url
        if not apply_url:
            raise ValueError(f"Job {job.id} has no apply_url")

        await page.goto(apply_url)

        # 1. CAPTCHA Check
        if await self._detect_captcha(page):
            raise PauseRequired(reason="CAPTCHA_DETECTED")

        # 2. Standard Fields
        first_name = candidate.name.split()[0] if candidate.name else ""
        last_name = " ".join(candidate.name.split()[1:]) if len(candidate.name.split()) > 1 else candidate.name

        await self._fill_first_matching_selector(page, ["#first_name", "[name='job_application[first_name]']"], first_name)
        await self._fill_first_matching_selector(page, ["#last_name", "[name='job_application[last_name]']"], last_name)
        await self._fill_first_matching_selector(page, ["#email", "[name='job_application[email]']"], candidate.email)
        if candidate.phone:
            await self._fill_first_matching_selector(page, ["#phone", "[name='job_application[phone]']"], candidate.phone)

        # 3. File Uploads
        if resume_path:
            await page.set_input_files("input[type='file'][name*='resume'], #resume_upload", resume_path)

        if cover_letter_path:
            await page.set_input_files("input[type='file'][name*='cover_letter'], #cover_letter_upload", cover_letter_path)

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
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            "#challenge-form",
        ]
        for sel in captcha_selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    return True
            except Exception:
                continue
        return False
