"""
backend/src/services/telegram_service.py

Telegram Bot Notification Service for Helios Mission Control.
Supports formatted HTML alerts, ATS match score reports, and photo screenshot uploads to @Helios_vinay_AI_Bot.
"""
from __future__ import annotations

import os
import json
import uuid
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any


class TelegramService:
    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None
    ):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "7636566180:AAGIZRXZRqD7gx-YfkRLGH3TpUyyqe55E0E")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "8466657787")

    def send_message(self, text: str) -> Dict[str, Any]:
        """Dispatches an HTML formatted text message to Telegram."""
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = json.dumps({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML"
        }).encode("utf-8")
        
        try:
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Helios/3.0 (Python/Urllib)"
                }
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def send_screenshot(self, photo_path: str, caption: str) -> Dict[str, Any]:
        """Uploads a DOM screenshot image directly to Telegram or sends structured HTML notification."""
        url = f"https://api.telegram.org/bot{self.token}/sendPhoto"
        
        if photo_path and os.path.exists(photo_path):
            try:
                with open(photo_path, "rb") as f:
                    img_bytes = f.read()

                bound = "----WebKitFormBoundary" + uuid.uuid4().hex
                body = bytearray()
                body.extend(f"--{bound}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{self.chat_id}\r\n".encode("utf-8"))
                body.extend(f"--{bound}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{caption}\r\n".encode("utf-8"))
                body.extend(f"--{bound}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))
                body.extend(f"--{bound}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{os.path.basename(photo_path)}\"\r\nContent-Type: image/png\r\n\r\n".encode("utf-8"))
                body.extend(img_bytes)
                body.extend(f"\r\n--{bound}--\r\n".encode("utf-8"))

                req = urllib.request.Request(
                    url,
                    data=bytes(body),
                    headers={
                        "Content-Type": f"multipart/form-data; boundary={bound}",
                        "User-Agent": "Helios/3.0 (Python/Urllib)"
                    }
                )
                with urllib.request.urlopen(req, timeout=15.0) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                # Fallback to text message if photo upload hits ISP/network timeout
                return self.send_message(f"📸 <b>[DOM Verification Screenshot]</b>\n\n{caption}")

        return self.send_message(caption)
