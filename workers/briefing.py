"""
workers/briefing.py

MorningBriefingGenerator — Formats and sends daily morning executive summaries to candidate Telegram.
Synthesizes jobs scanned, eligibility passes, application submissions, and upcoming interview schedules.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from automation.notification import TelegramNotifier
from shared.telemetry.metrics import HeliosSessionMetrics


class MorningBriefingGenerator:
    """
    Generates structured daily executive briefings.
    """

    def __init__(self, notifier: Optional[TelegramNotifier] = None):
        self.notifier = notifier or TelegramNotifier()

    def format_briefing(self, metrics: HeliosSessionMetrics) -> str:
        """
        Formats daily briefing summary string.
        """
        today_str = datetime.now().strftime("%A, %d %B %Y")

        rejection_summary = "\n".join(
            f"  • {count} → {reason}"
            for reason, count in sorted(metrics.rejection_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
        ) or "  • None"

        return (
            f"☀ **Good morning Vinay — {today_str}**\n\n"
            f"Yesterday Helios Automation:\n"
            f"  ✓ **Scanned**: {metrics.jobs_scanned:,} job postings\n"
            f"  ✓ **Eligible**: {metrics.jobs_eligible} (passed hard rules)\n"
            f"  ✓ **Excellent**: {metrics.excellent_matches} matches (score ≥ 85%)\n"
            f"  ✓ **Applied**: {metrics.auto_applied} (auto-submitted)\n"
            f"  ⏳ **Awaiting Approval**: {metrics.awaiting_approval}\n"
            f"  ⚠️ **Paused (CAPTCHA/OTP)**: {metrics.paused_captcha}\n\n"
            f"**Top Rejection Reasons**:\n"
            f"{rejection_summary}\n\n"
            f"⚡ **Avg application time**: {metrics.avg_application_time_seconds:.1f} seconds"
        )

    async def send_briefing(self, metrics: HeliosSessionMetrics) -> bool:
        """
        Sends briefing message via TelegramNotifier.
        """
        text = self.format_briefing(metrics)
        if self.notifier.bot_token and self.notifier.chat_id:
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"https://api.telegram.org/bot{self.notifier.bot_token}/sendMessage",
                        json={
                            "chat_id": self.notifier.chat_id,
                            "text": text,
                            "parse_mode": "Markdown",
                        },
                        timeout=5.0,
                    )
                return True
            except Exception as e:
                print(f"MorningBriefingGenerator send warning: {e}")
        return False
