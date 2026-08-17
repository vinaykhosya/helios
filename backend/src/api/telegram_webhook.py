"""
backend/src/api/telegram_webhook.py
HMAC-verified Telegram callback handler for inline keyboard buttons.
Fails closed in production if secret is unconfigured.
"""
from __future__ import annotations
import hashlib, hmac, json, os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.src.api.deps import get_db
from backend.src.repositories.human_queue import SQLAlchemyHumanQueueRepository

router = APIRouter(prefix="/api/telegram", tags=["Telegram"])


@router.post("/callback")
async def telegram_callback(request: Request, session: AsyncSession = Depends(get_db)):
    env = os.getenv("ENVIRONMENT", "development").lower()
    secret = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")

    # Production fail-closed security rule
    if env == "production" and not secret:
        raise HTTPException(
            status_code=503,
            detail="Telegram webhook secret is not configured in production environment.",
        )

    # Verify webhook secret token if configured
    if secret:
        sig = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not hmac.compare_digest(sig, secret):
            raise HTTPException(status_code=403, detail="Invalid webhook token")

    body = await request.json()
    callback = body.get("callback_query", {})
    data = callback.get("data", "")
    chat_id = str(callback.get("message", {}).get("chat", {}).get("id", ""))

    allowed_chat = os.getenv("TELEGRAM_CHAT_ID", "")
    if allowed_chat and chat_id != allowed_chat:
        raise HTTPException(status_code=403, detail="Unauthorized chat")

    # data format: "approve:{entry_id}" or "skip:{entry_id}"
    if ":" not in data:
        return {"ok": True}

    action, entry_id = data.split(":", 1)
    repo = SQLAlchemyHumanQueueRepository(session)
    try:
        if action == "approve":
            await repo.decide(entry_id, "approved")
        elif action == "skip":
            await repo.decide(entry_id, "skipped")
    except (LookupError, ValueError) as e:
        print(f"[TelegramCallback] {e}")

    return {"ok": True}
