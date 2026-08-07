"""
automation/notification.py

TelegramNotifier — Human-in-the-loop notification bot for application approval requests,
CAPTCHA/OTP pause alerts, and morning executive briefings.
"""
from __future__ import annotations

import uuid
from typing import Optional
from pydantic import BaseModel, Field

from core.models.job import Job
from intelligence.ranking.ranker import RankingResult


class PendingApproval(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    job_id: str
    job_title: str
    company: str
    confidence: float
    pause_reason: Optional[str] = None
    status: str = "pending"  # "pending" | "approved" | "skipped"


class TelegramNotifier:
    """
    Sends Telegram messages and inline approval buttons to user.
    """

    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._pending: dict[str, PendingApproval] = {}

    def format_approval_message(self, job: Job, ranking: RankingResult, pause_reason: Optional[str] = None) -> str:
        """
        Formats human-in-the-loop approval message in HTML.
        """
        matched_str = ", ".join([d.name for d in ranking.dimensions if d.matched]) or "None"
        missing_str = ", ".join(ranking.missing_skills[:3]) if ranking.missing_skills else "None"
        reason_header = f"\n⚠️ <b>Pause Reason</b>: {pause_reason}" if pause_reason else ""

        return (
            f"🔔 <b>Helios — Application Approval Required</b>\n"
            f"{reason_header}\n"
            f"📋 <b>Job</b>: {job.title}\n"
            f"🏢 <b>Company</b>: {job.company}\n"
            f"📍 <b>Location</b>: {job.location or 'Not specified'}\n"
            f"🎯 <b>Match Score</b>: {int(ranking.overall_score * 100)}% (Confidence: {int(ranking.confidence * 100)}%)\n\n"
            f"✅ <b>Matched Criteria</b>: {matched_str}\n"
            f"❌ <b>Missing Keywords</b>: {missing_str}\n\n"
            f"<i>Reply /approve or /skip to confirm application submit</i>"
        )

    async def send_approval_request(
        self,
        job: Job,
        ranking: RankingResult,
        pause_reason: Optional[str] = None,
    ) -> PendingApproval:
        """
        Creates pending approval record and sends notification.
        """
        pending = PendingApproval(
            job_id=str(job.id),
            job_title=job.title,
            company=job.company,
            confidence=ranking.confidence,
            pause_reason=pause_reason,
        )
        self._pending[pending.id] = pending

        msg = self.format_approval_message(job, ranking, pause_reason)

        if self.bot_token and self.chat_id:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                        json={
                            "chat_id": self.chat_id,
                            "text": msg,
                            "parse_mode": "HTML",
                        },
                        timeout=10.0,
                    )
                    if resp.status_code != 200:
                        print(f"Telegram API warning response: {resp.text}")
            except Exception as e:
                print(f"TelegramNotifier error: {e}")

        return pending

    async def respond(self, pending_id: str, approved: bool) -> bool:
        """
        Responds to a pending approval request.
        """
        if pending_id not in self._pending:
            return False

        item = self._pending[pending_id]
        item.status = "approved" if approved else "skipped"
        return True
