"""
backend/src/services/telegram_service.py

Telegram Bot Notification Service for Helios Mission Control.
Supports text messages, HTML formatting, and direct DOM screenshot uploads to @Helios_vinay_AI_Bot.
"""
from __future__ import annotations

import os
import httpx
from typing import Optional, Dict, Any


class TelegramService:
    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "7636566180:AAGIZRXZRqD7gx-YfkRLGH3TpUyyqe55E0E")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "8466657787")

    async def send_message(self, text: str) -> Dict[str, Any]:
        """Dispatches an HTML formatted text message to Telegram."""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                return resp.json()
        except Exception as e:
            return {"ok": False, "error": str(e)}

    async def send_screenshot(self, photo_path: str, caption: str) -> Dict[str, Any]:
        """Uploads a DOM screenshot image directly to Telegram with a caption."""
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        try:
            if os.path.exists(photo_path):
                async with httpx.AsyncClient(timeout=30.0) as client:
                    with open(photo_path, "rb") as f:
                        files = {"photo": (os.path.basename(photo_path), f, "image/png")}
                        data = {"chat_id": self.chat_id, "caption": caption, "parse_mode": "HTML"}
                        resp = await client.post(url, data=data, files=files)
                        return resp.json()
            else:
                return await self.send_message(f"{caption}\n(Screenshot file missing at {photo_path})")
        except Exception as e:
            return await self.send_message(f"{caption}\n(Screenshot upload notice: {e})")
