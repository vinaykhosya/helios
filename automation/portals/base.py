"""
automation/portals/base.py

Base Abstract Portal Adapter & Authentication State definitions for Helios v4.0.
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional


class AuthState(Enum):
    AUTHENTICATED = "authenticated"
    LOGIN_REQUIRED = "login_required"
    MFA_REQUIRED = "mfa_required"
    CAPTCHA_REQUIRED = "captcha_required"
    EXPIRED = "expired"
    UNKNOWN = "unknown"


class PortalAdapter(ABC):
    def __init__(self, portal_name: str, ats_type: str = "generic"):
        self.portal_name = portal_name.lower().strip()
        self.ats_type = ats_type.lower().strip()

    @abstractmethod
    async def detect_auth_state(self, page) -> AuthState:
        """Detects whether current Playwright context page is logged in, requires credentials, or hit CAPTCHA."""
        pass

    @abstractmethod
    async def perform_login(self, page, credentials: Dict[str, str]) -> bool:
        """Executes auto-login using decrypted credentials from EncryptedCredentialVault."""
        pass

    @abstractmethod
    async def search_requisitions(self, page, query: str, location: str = "India") -> list:
        """Performs portal-first search for target active requisitions."""
        pass

    @abstractmethod
    async def fill_requisition_form(self, page, candidate_profile: dict, resume_pdf_path: str) -> bool:
        """Executes multi-step form filler for target application."""
        pass
