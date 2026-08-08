"""
automation/intelligence/contracts.py

Helios v5.0 Universal Intelligence Data Contracts.
- Enforces strict data contracts across PageUnderstandingEngine, SemanticMapper, ExecutionPlanner, ActionExecutor, and EvidenceVerifier.
- Preserves complete forensic execution metadata (ActionExecution, EvidencePayload).
- Enforces hard safety invariants (submission_allowed, recovery_required).
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Union
import time


class ElementSemantic(Enum):
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    FULL_NAME = "full_name"
    EMAIL = "email"
    PHONE = "phone"
    ORGANIZATION = "organization"
    LINKEDIN = "linkedin"
    GITHUB = "github"
    WEBSITE = "website"
    RESUME_UPLOAD = "resume_upload"
    CUSTOM_QUESTION = "custom_question"
    CHECKBOX_CONSENT = "checkbox_consent"
    NEXT_STEP = "next_step"
    SUBMIT_APPLICATION = "submit_application"
    UNKNOWN = "unknown"


class ActionType(Enum):
    FILL = "FILL"
    ATTACH = "ATTACH"
    CHECK = "CHECK"
    CLICK = "CLICK"


class PageType(Enum):
    APPLICATION_FORM = "APPLICATION_FORM"
    JOB_DESCRIPTION = "JOB_DESCRIPTION"
    THANK_YOU_CONFIRMATION = "THANK_YOU_CONFIRMATION"
    CAPTCHA_CHALLENGE = "CAPTCHA_CHALLENGE"
    LOGIN_REQUIRED = "LOGIN_REQUIRED"
    UNKNOWN = "UNKNOWN"


class RecoveryReason(Enum):
    NONE = "NONE"
    UNRESOLVED_SENSITIVE_QUESTION = "UNRESOLVED_SENSITIVE_QUESTION"
    CAPTCHA_OR_MFA_DETECTED = "CAPTCHA_OR_MFA_DETECTED"
    SUBMISSION_CONFIDENCE_LOW = "SUBMISSION_CONFIDENCE_LOW"
    MANDATORY_LOGIN_REQUIRED = "MANDATORY_LOGIN_REQUIRED"
    FIELD_FILL_FAILURE = "FIELD_FILL_FAILURE"
    POLICY_DISALLOWED = "POLICY_DISALLOWED"


@dataclass
class DetectedElement:
    element_id: str
    selector_used: str
    tag_name: str
    element_type: str
    semantic: ElementSemantic
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence {self.confidence} out of bounds [0.0, 1.0]")


@dataclass
class PageSchema:
    page_type: PageType
    ats_type: str                            # "workday", "lever", "greenhouse", "ashby", "generic"
    fields: List[DetectedElement] = field(default_factory=list)
    buttons: List[DetectedElement] = field(default_factory=list)
    has_captcha: bool = False
    has_login_prompt: bool = False


@dataclass
class PlannedAction:
    action_id: str
    action_type: ActionType
    target_semantic: ElementSemantic
    target_selector: str
    value_to_fill: Optional[str] = None
    confidence: float = 1.0

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence {self.confidence} out of bounds [0.0, 1.0]")


@dataclass
class ExecutionPlan:
    page_type: PageType
    actions: List[PlannedAction] = field(default_factory=list)
    submission_allowed: bool = False
    recovery_required: bool = False
    recovery_reason: RecoveryReason = RecoveryReason.NONE
    min_action_confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "page_type": self.page_type.value,
            "actions_count": len(self.actions),
            "submission_allowed": self.submission_allowed,
            "recovery_required": self.recovery_required,
            "recovery_reason": self.recovery_reason.value,
            "min_action_confidence": self.min_action_confidence
        }


@dataclass
class ActionExecution:
    action_id: str
    action_type: ActionType
    target_semantic: ElementSemantic
    target_selector: str
    attempted: bool
    succeeded: bool
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))


@dataclass
class EvidencePayload:
    submit_clicked: bool
    live_dom_confirmation: bool
    application_id: Optional[str] = None
    application_id_source: Optional[str] = None    # "LIVE_PORTAL_DOM", "NONE", "TEST_MOCK"
    url_before: str = ""
    url_after: str = ""
    actions: List[ActionExecution] = field(default_factory=list)
    screenshot_path: Optional[str] = None
    verified_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def is_strong_evidence(self) -> bool:
        """GOLDEN RULE: Must have clicked submit and derived live DOM confirmation or live portal ID."""
        if not self.submit_clicked:
            return False
        if self.application_id_source != "LIVE_PORTAL_DOM" and not self.live_dom_confirmation:
            return False
        return self.live_dom_confirmation or bool(self.application_id)
