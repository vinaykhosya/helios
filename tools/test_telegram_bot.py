import asyncio
import os
from core.models.job import Job, JobSource
from intelligence.ranking.ranker import RankingResult, MatchDimension
from automation.notification import TelegramNotifier

async def test_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "7636566180:AAGIZRXZRqD7gx-YfkRLGH3TpUyyqe55E0E")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "8466657787")

    notifier = TelegramNotifier(bot_token=token, chat_id=chat_id)

    job = Job(
        source=JobSource.GREENHOUSE,
        source_id="1",
        source_url="https://boards.greenhouse.io/siemens/jobs/1",
        apply_url="https://boards.greenhouse.io/siemens/jobs/1",
        title="AI Engineer & Automation Lead",
        company="Siemens AI",
        location="India (Remote)",
    )

    ranking = RankingResult(
        job_id="job_123",
        overall_score=0.96,
        confidence=0.98,
        dimensions=[
            MatchDimension(name="Tech Stack", score=0.95, weight=0.4, matched=True),
            MatchDimension(name="Location", score=1.0, weight=0.2, matched=True),
        ],
        missing_skills=["Kubernetes"],
        recommendation="auto_apply",
        reason="Excellent 96% fit score across Tech Stack and Location alignment.",
    )

    print(f"Sending live approval request to Telegram Chat ID {chat_id}...")
    pending = await notifier.send_approval_request(job=job, ranking=ranking)
    print(f"Notification Sent! Pending ID: {pending.id}, Status: {pending.status}")

if __name__ == "__main__":
    asyncio.run(test_telegram())
