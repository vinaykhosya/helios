"""
backend/src/services/action_token_service.py

ActionTokenService — Fernet-signed expiring tokens for the Mark Applied link.

The token encodes: application_id, user_id, action, expires_at.
It is embedded in the __helios_mark_applied_url column of each Google Sheet row.
When the user clicks the link and submits the confirmation form, the token is
validated before any state mutation occurs.

Generate a production key:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
Set as HELIOS_ACTION_TOKEN_SECRET in .env.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


TOKEN_TTL_HOURS = int(os.getenv("HELIOS_ACTION_TOKEN_TTL_HOURS", "168"))  # 7 days


def _get_fernet() -> Fernet:
    secret = os.getenv("HELIOS_ACTION_TOKEN_SECRET")
    env = os.getenv("ENVIRONMENT", "development").lower()

    if not secret:
        if env == "production":
            raise RuntimeError(
                "HELIOS_ACTION_TOKEN_SECRET must be set in production environment. "
                "Failing startup to prevent ephemeral token generation."
            )
        import warnings
        warnings.warn(
            "HELIOS_ACTION_TOKEN_SECRET not set. "
            "Tokens will not survive server restarts. Set this in .env for production.",
            stacklevel=3,
        )
        if not hasattr(_get_fernet, "_key") or _get_fernet._key is None:
            _get_fernet._key = Fernet.generate_key()
        secret = _get_fernet._key.decode()
    return Fernet(secret.encode() if isinstance(secret, str) else secret)


class ActionToken:
    def __init__(self, application_id: str, user_id: str, action: str, expires_at: datetime):
        self.application_id = application_id
        self.user_id = user_id
        self.action = action
        self.expires_at = expires_at

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at


class TokenValidationError(Exception):
    """Never expose the reason for failure to end-user (prevents oracle attacks)."""
    pass


class ActionTokenService:

    def create_mark_applied_token(
        self, application_id: str, user_id: str, ttl_hours: int = TOKEN_TTL_HOURS
    ) -> str:
        """Returns URL-safe Fernet token string."""
        f = _get_fernet()
        payload = {
            "application_id": application_id,
            "user_id": user_id,
            "action": "mark_applied",
            "exp": (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat(),
        }
        return f.encrypt(json.dumps(payload).encode()).decode()

    def validate(
        self,
        token: str,
        expected_action: str = "mark_applied",
        expected_application_id: Optional[str] = None,
    ) -> ActionToken:
        """
        Decode and validate. Raises TokenValidationError on any failure.
        Checks: signature, expiry, action match, application_id binding (if provided).
        """
        try:
            f = _get_fernet()
            raw = f.decrypt(token.encode())
            payload = json.loads(raw)
        except (InvalidToken, json.JSONDecodeError, Exception):
            raise TokenValidationError("Invalid or tampered token")

        if payload.get("action") != expected_action:
            raise TokenValidationError("Token action mismatch")

        try:
            expires_at = datetime.fromisoformat(payload["exp"])
        except (KeyError, ValueError):
            raise TokenValidationError("Invalid token expiry")

        if datetime.now(timezone.utc) > expires_at:
            raise TokenValidationError("Token has expired")

        if expected_application_id and payload.get("application_id") != expected_application_id:
            raise TokenValidationError("Token application_id mismatch")

        return ActionToken(
            application_id=payload["application_id"],
            user_id=payload["user_id"],
            action=payload["action"],
            expires_at=expires_at,
        )
