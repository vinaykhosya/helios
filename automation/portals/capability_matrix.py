"""
automation/portals/capability_matrix.py

Helios v5.0 ATS Capability Matrix.
Tracks capability status across supported ATS vendors: WORKDAY, LEVER, GREENHOUSE, ASHBY, GENERIC.
"""
from dataclasses import dataclass, field
from typing import Dict, Any, List
from enum import Enum


class CapabilityStatus(Enum):
    SUPPORTED = "SUPPORTED"
    PARTIAL = "PARTIAL"
    UNSUPPORTED = "UNSUPPORTED"
    BLOCKED = "BLOCKED"
    NOT_TESTED = "NOT_TESTED"


@dataclass
class ATSCapabilityProfile:
    ats_name: str
    job_detail_navigation: CapabilityStatus = CapabilityStatus.SUPPORTED
    apply_resolution: CapabilityStatus = CapabilityStatus.SUPPORTED
    authentication: CapabilityStatus = CapabilityStatus.SUPPORTED
    resume_upload: CapabilityStatus = CapabilityStatus.SUPPORTED
    resume_processing: CapabilityStatus = CapabilityStatus.SUPPORTED
    multi_page_forms: CapabilityStatus = CapabilityStatus.SUPPORTED
    required_field_detection: CapabilityStatus = CapabilityStatus.SUPPORTED
    review_detection: CapabilityStatus = CapabilityStatus.SUPPORTED
    submit_detection: CapabilityStatus = CapabilityStatus.SUPPORTED
    post_submit_confirmation: CapabilityStatus = CapabilityStatus.SUPPORTED
    application_id_extraction: CapabilityStatus = CapabilityStatus.SUPPORTED
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
            multi_page_forms=CapabilityStatus.SUPPORTED,
            resume_processing=CapabilityStatus.SUPPORTED,
            application_id_extraction=CapabilityStatus.SUPPORTED
        ),
        "lever": ATSCapabilityProfile(
            ats_name="LEVER",
            multi_page_forms=CapabilityStatus.PARTIAL,
            resume_processing=CapabilityStatus.SUPPORTED,
            application_id_extraction=CapabilityStatus.SUPPORTED
        ),
        "greenhouse": ATSCapabilityProfile(
            ats_name="GREENHOUSE",
            multi_page_forms=CapabilityStatus.PARTIAL,
            resume_processing=CapabilityStatus.SUPPORTED,
            application_id_extraction=CapabilityStatus.SUPPORTED
        ),
        "ashby": ATSCapabilityProfile(
            ats_name="ASHBY",
            multi_page_forms=CapabilityStatus.PARTIAL,
            resume_processing=CapabilityStatus.SUPPORTED,
            application_id_extraction=CapabilityStatus.SUPPORTED
        ),
        "generic": ATSCapabilityProfile(
            ats_name="GENERIC",
            multi_page_forms=CapabilityStatus.PARTIAL,
            resume_processing=CapabilityStatus.PARTIAL,
            application_id_extraction=CapabilityStatus.PARTIAL
        )
    }

    @classmethod
    def get_profile(cls, ats_name: str) -> ATSCapabilityProfile:
        name_clean = ats_name.lower().strip()
        return cls._PROFILES.get(name_clean, cls._PROFILES["generic"])

    @classmethod
    def get_all_profiles(cls) -> Dict[str, Dict[str, Any]]:
        return {k: v.to_dict() for k, v in cls._PROFILES.items()}
