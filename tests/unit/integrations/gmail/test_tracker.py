"""
tests/unit/integrations/gmail/test_tracker.py

Unit tests for GmailOutcomeTracker and safe outcome status updates.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from integrations.gmail.tracker import GmailOutcomeTracker, OutcomeUpdate
from integrations.gmail.matcher import EmailApplicationMatcher


@pytest.fixture
def mock_app_repo():
    repo = MagicMock()
    repo.update_status = AsyncMock()
    return repo


@pytest.mark.asyncio
async def test_poll_returns_empty_when_no_credentials(mock_app_repo):
    tracker = GmailOutcomeTracker()
    res = await tracker.poll_and_update("", mock_app_repo)
    assert res == []
    assert mock_app_repo.update_status.call_count == 0


@pytest.mark.asyncio
async def test_process_message_rejection_unambiguous_mutates_status(mock_app_repo):
    tracker = GmailOutcomeTracker()
    matcher = EmailApplicationMatcher()

    open_apps = [
        {
            "id": "app-postman-1",
            "company_name": "Postman",
            "company_domain": "postman.com",
            "job_title": "Backend Engineer",
            "apply_url": "https://jobs.postman.com/123",
            "status": "applied",
        }
    ]

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = {
        "payload": {
            "headers": [
                {"name": "From", "Value": "jobs@postman.com", "value": "jobs@postman.com"},
                {"name": "Subject", "Value": "Postman Application Update", "value": "Postman Application Update"},
            ]
        },
        "snippet": "Thank you for applying. We regret to inform you that we are not moving forward with your candidacy.",
    }

    update = await tracker._process_message(mock_service, "msg-123", matcher, open_apps)
    assert update is not None
    assert update.mutated is True
    assert update.classified_status == "rejected"
    assert update.application_id == "app-postman-1"


@pytest.mark.asyncio
async def test_process_message_ambiguous_match_does_not_mutate(mock_app_repo):
    """
    CRITICAL INVARIANT: When multiple applications exist for same domain,
    the outcome tracker MUST NOT mutate state.
    """
    tracker = GmailOutcomeTracker()
    matcher = EmailApplicationMatcher()

    open_apps = [
        {"id": "app-g-swe", "company_name": "Google", "company_domain": "google.com", "job_title": "SWE", "apply_url": "", "status": "applied"},
        {"id": "app-g-ml", "company_name": "Google", "company_domain": "google.com", "job_title": "ML Engineer", "apply_url": "", "status": "applied"},
    ]

    mock_service = MagicMock()
    mock_service.users().messages().get().execute.return_value = {
        "payload": {
            "headers": [
                {"name": "From", "value": "recruiting@google.com"},
                {"name": "Subject", "value": "Google Application Status Update"},
            ]
        },
        "snippet": "We regret to inform you that we are moving forward with other candidates.",
    }

    update = await tracker._process_message(mock_service, "msg-456", matcher, open_apps)
    assert update is not None
    assert update.mutated is False
    assert update.classified_status == "AMBIGUOUS"
    assert update.application_id is None
    assert mock_app_repo.update_status.call_count == 0


@pytest.mark.asyncio
async def test_classify_email_fallback_rules():
    tracker = GmailOutcomeTracker()

    with patch.dict("os.environ", {"OPENAI_API_KEY": ""}, clear=False):
        label, conf = await tracker._classify_email(
            "Application update", "We regret to inform you that your application was unsuccessful."
        )
        assert label == "REJECTION"
        assert conf >= 0.80

        label, conf = await tracker._classify_email(
            "Online Assessment Invite", "Please complete your HackerRank technical assessment within 48 hours."
        )
        assert label == "OA_INVITE"

        label, conf = await tracker._classify_email(
            "Introductory Call", "Let's schedule a 15-minute phone screen to discuss the role."
        )
        assert label == "PHONE_SCREEN"

        label, conf = await tracker._classify_email(
            "Offer Letter", "We are pleased to offer you the position of Senior Engineer!"
        )
        assert label == "OFFER"
