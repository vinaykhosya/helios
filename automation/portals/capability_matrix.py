"""
automation/portals/capability_matrix.py

Helios v5.0 ATS Capability Matrix.
Tracks capability status across supported ATS vendors: WORKDAY, LEVER, GREENHOUSE, ASHBY, GENERIC.
Enforces strict empirical verification taxonomy:
  - IMPLEMENTED: Code exists but not yet empirically verified live.
  - EMPIRICALLY_VERIFIED: Demonstrated end-to-end in a live portal run.
  - PARTIAL: Works for subset of tenants/pages.
  - UNVERIFIED: Untested or failed live verification.
  - BLOCKED: Navigation/Anti-bot/Captcha blocked.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum


class CapabilityStatus(Enum):
    IMPLEMENTED = "IMPLEMENTED"
    EMPIRICALLY_VERIFIED = "EMPIRICALLY_VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    BLOCKED = "BLOCKED"


@dataclass
class ATSCapabilityProfile:
    ats_name: str
    job_detail_navigation: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    apply_resolution: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    authentication: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    resume_upload: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    resume_processing: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    multi_page_forms: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    required_field_detection: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    review_detection: CapabilityStatus = CapabilityStatus.IMPLEMENTED
    submit_detection: CapabilityStatus = CapabilityStatus.UNVERIFIED
    post_submit_confirmation: CapabilityStatus = CapabilityStatus.UNVERIFIED
    application_id_extraction: CapabilityStatus = CapabilityStatus.UNVERIFIED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ats_name": self.ats_name,
            "capabilities": {
                "job_detail_navigation": self.job_detail_navigation.value,
                "apply_resolution": self.apply_resolution.value,
                "authentication": self.authentication.value,
                "resume_upload": self.resume_upload.value,
                "resume_processing": self.resume_processing.value,
                "multi_page_forms": self.multi_page_forms.value,
                "required_field_detection": self.required_field_detection.value,
                "review_detection": self.review_detection.value,
                "submit_detection": self.submit_detection.value,
                "post_submit_confirmation": self.post_submit_confirmation.value,
                "application_id_extraction": self.application_id_extraction.value,
            },
            "metadata": self.metadata
        }


class ATSCapabilityMatrix:
    _PROFILES: Dict[str, ATSCapabilityProfile] = {
        "workday": ATSCapabilityProfile(
            ats_name="WORKDAY",
            submit_detection=CapabilityStatus.UNVERIFIED,
            post_submit_confirmation=CapabilityStatus.UNVERIFIED,
            application_id_extraction=CapabilityStatus.UNVERIFIED
        ),
        "lever": ATSCapabilityProfile(
            ats_name="LEVER",
            resume_processing=CapabilityStatus.EMPIRICALLY_VERIFIED,
            submit_detection=CapabilityStatus.UNVERIFIED,
            post_submit_confirmation=CapabilityStatus.UNVERIFIED,
            application_id_extraction=CapabilityStatus.UNVERIFIED
        ),
        "greenhouse": ATSCapabilityProfile(
            ats_name="GREENHOUSE",
            submit_detection=CapabilityStatus.UNVERIFIED,
            post_submit_confirmation=CapabilityStatus.UNVERIFIED,
            application_id_extraction=CapabilityStatus.UNVERIFIED
        ),
        "ashby": ATSCapabilityProfile(
            ats_name="ASHBY",
            submit_detection=CapabilityStatus.UNVERIFIED,
            post_submit_confirmation=CapabilityStatus.UNVERIFIED,
            application_id_extraction=CapabilityStatus.UNVERIFIED
        ),
        "generic": ATSCapabilityProfile(
            ats_name="GENERIC",
            submit_detection=CapabilityStatus.UNVERIFIED,
            post_submit_confirmation=CapabilityStatus.UNVERIFIED,
            application_id_extraction=CapabilityStatus.UNVERIFIED
        )
    }

    @classmethod
    def get_profile(cls, ats_name: str) -> ATSCapabilityProfile:
        name_clean = ats_name.lower().strip()
        return cls._PROFILES.get(name_clean, cls._PROFILES["generic"])

    @classmethod
    def mark_capability(cls, ats_name: str, capability_name: str, status: CapabilityStatus):
        profile = cls.get_profile(ats_name)
        if hasattr(profile, capability_name):
            setattr(profile, capability_name, status)

    @classmethod
    def get_all_profiles(cls) -> Dict[str, Dict[str, Any]]:
        return {k: v.to_dict() for k, v in cls._PROFILES.items()}
