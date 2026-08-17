"""
tests/unit/services/test_action_token_service.py

Unit tests for ActionTokenService.
"""
import os
import time
import pytest
from cryptography.fernet import Fernet

os.environ["HELIOS_ACTION_TOKEN_SECRET"] = Fernet.generate_key().decode()
from backend.src.services.action_token_service import ActionTokenService, TokenValidationError


def svc():
    return ActionTokenService()


def test_create_and_validate():
    t = svc().create_mark_applied_token("app-1", "user-1")
    d = svc().validate(t)
    assert d.application_id == "app-1"
    assert d.user_id == "user-1"
    assert not d.is_expired


def test_tampered_raises():
    t = svc().create_mark_applied_token("app-1", "user-1")
    with pytest.raises(TokenValidationError):
        svc().validate(t[:-4] + "XXXX")


def test_wrong_app_id_raises():
    t = svc().create_mark_applied_token("app-real", "user-1")
    with pytest.raises(TokenValidationError, match="mismatch"):
        svc().validate(t, expected_application_id="app-other")


def test_correct_app_id_passes():
    t = svc().create_mark_applied_token("app-real", "user-1")
    d = svc().validate(t, expected_application_id="app-real")
    assert d.application_id == "app-real"


def test_expired_raises():
    t = svc().create_mark_applied_token("app-1", "user-1", ttl_hours=0)
    time.sleep(0.01)
    with pytest.raises(TokenValidationError, match="expired"):
        svc().validate(t)


def test_token_is_string():
    t = svc().create_mark_applied_token("app-1", "user-1")
    assert isinstance(t, str) and len(t) > 50


def test_wrong_action_raises():
    t = svc().create_mark_applied_token("app-1", "user-1")
    with pytest.raises(TokenValidationError, match="action mismatch"):
        svc().validate(t, expected_action="other_action")
