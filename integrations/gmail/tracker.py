"""
integrations/gmail/tracker.py

GmailOutcomeTracker — polls Gmail for recruiter emails and updates application status.
Uses EmailApplicationMatcher for safe matching (AMBIGUOUS = no-op).
Classifies email intent with a lightweight LLM call (subject + 500 chars snippet only).
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass
from typing import Optional

from integrations.gmail.matcher import EmailApplicationMatcher, MatchConfidence


CLASSIFICATION_PROMPT = """Classify this recruiter email into exactly one of:
REJECTION, OA_INVITE, PHONE_SCREEN, INTERVIEW_INVITE, OFFER, UNKNOWN

Subject: {subject}
Body preview: {body}

Respond with only the classification label and a confidence 0.0-1.0.
Format: LABEL|0.85"""

STATUS_MAP = {
    "REJECTION":        "rejected",
    "OA_INVITE":        "technical",
    "PHONE_SCREEN":     "phone_screen",
    "INTERVIEW_INVITE": "technical",
    "OFFER":            "offer",
}


@dataclass
class OutcomeUpdate:
    message_id: str
    company_domain: str
    subject: str
    classified_status: str
    confidence: float
    application_id: Optional[str]
    mutated: bool


class GmailOutcomeTracker:
    MIN_CONFIDENCE = 0.80
    POLL_LABEL = "INBOX"
    MAX_RESULTS = 50

    def __init__(self):
        self._processed_message_ids: set[str] = set()

    async def poll_and_update(
        self,
        credentials_json: str,
        app_repo,
        user_id: str = "user_default",
    ) -> list[OutcomeUpdate]:
        """Poll Gmail and update application statuses safely. Call periodically."""
        if not credentials_json:
            return []

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            creds = Credentials.from_authorized_user_info(
                __import__("json").loads(credentials_json),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            )
            service = build("gmail", "v1", credentials=creds)
        except Exception as e:
            print(f"[Gmail] Auth/Client init failed: {e}")
            return []

        open_apps = await app_repo.list_open_with_company_info(user_id)
        matcher = EmailApplicationMatcher()
        updates: list[OutcomeUpdate] = []

        try:
            result = service.users().messages().list(
                userId="me",
                labelIds=[self.POLL_LABEL],
                maxResults=self.MAX_RESULTS,
                q="from:(@greenhouse.io OR @lever.co OR @ashbyhq.com OR @workday.com OR @smartrecruiters.com)",
            ).execute()
            messages = result.get("messages", [])
        except Exception as e:
            print(f"[Gmail] List messages failed: {e}")
            return []

        for msg in messages:
            msg_id = msg.get("id")
            if not msg_id or msg_id in self._processed_message_ids:
                continue

            update = await self._process_message(
                service, msg_id, matcher, open_apps
            )
            if update:
                self._processed_message_ids.add(msg_id)
                if update.mutated and update.application_id:
                    try:
                        await app_repo.update_status(update.application_id, update.classified_status)
                    except Exception as e:
                        print(f"[Gmail] Status update failed: {e}")
                updates.append(update)

        return updates

    async def _process_message(
        self,
        service,
        message_id: str,
        matcher: EmailApplicationMatcher,
        open_apps: list[dict],
    ) -> Optional[OutcomeUpdate]:
        try:
            msg = service.users().messages().get(
                userId="me",
                id=message_id,
                format="metadata",
                metadataHeaders=["From", "Subject"],
            ).execute()
        except Exception:
            return None

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = headers.get("From", "")
        subject = headers.get("Subject", "")

        # Extract sender domain
        domain_match = re.search(r"@([\w.-]+)", sender)
        if not domain_match:
            return None
        company_domain = domain_match.group(1).lower()

        # Body preview (subject + snippet max 500 chars, never full body)
        body_preview = msg.get("snippet", "")[:500]

        # Safe matching
        match = matcher.match(
            sender_email=sender,
            sender_domain=company_domain,
            subject=subject,
            body_preview=body_preview,
            open_applications=open_apps,
        )

        if match.is_ambiguous:
            print(f"[Gmail] AMBIGUOUS match ({match.matched_on}) — NO MUTATION")
            return OutcomeUpdate(
                message_id=message_id,
                company_domain=company_domain,
                subject=subject[:200],
                classified_status="AMBIGUOUS",
                confidence=0.0,
                application_id=None,
                mutated=False,
            )

        if not match.safe_to_mutate:
            return None

        # Classify only if match is safe
        classified_status, confidence = await self._classify_email(subject, body_preview)

        if confidence < self.MIN_CONFIDENCE:
            return OutcomeUpdate(
                message_id=message_id,
                company_domain=company_domain,
                subject=subject[:200],
                classified_status=classified_status,
                confidence=confidence,
                application_id=match.application_id,
                mutated=False,
            )

        new_status = STATUS_MAP.get(classified_status)
        if not new_status:
            return None

        return OutcomeUpdate(
            message_id=message_id,
            company_domain=company_domain,
            subject=subject[:200],
            classified_status=new_status,
            confidence=confidence,
            application_id=match.application_id,
            mutated=True,
        )

    async def _classify_email(self, subject: str, body: str) -> tuple[str, float]:
        """
        Classify email intent. Returns (status, confidence).
        Snippet-limited: never sends more than 500 characters of email body.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Rule-based fallback classifier if LLM key not configured
            lower = (subject + " " + body).lower()
            if any(w in lower for w in ("regret to inform", "not moving forward", "other candidates", "unsuccessful")):
                return "REJECTION", 0.95
            elif any(w in lower for w in ("online assessment", "hackerrank", "codesignal", "technical assessment")):
                return "OA_INVITE", 0.90
            elif any(w in lower for w in ("phone screen", "introductory call", "chat with our recruiter", "15-minute")):
                return "PHONE_SCREEN", 0.85
            elif any(w in lower for w in ("interview invite", "schedule an interview", "technical round")):
                return "INTERVIEW_INVITE", 0.90
            elif any(w in lower for w in ("offer of employment", "pleased to offer", "official offer")):
                return "OFFER", 0.95
            return "UNKNOWN", 0.0

        try:
            import httpx
            prompt = CLASSIFICATION_PROMPT.format(subject=subject, body=body[:500])
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 20,
                        "temperature": 0,
                    },
                )
                text = resp.json()["choices"][0]["message"]["content"].strip()
                label, conf_str = text.split("|")
                return label.strip(), float(conf_str.strip())
        except Exception:
            return "UNKNOWN", 0.0
