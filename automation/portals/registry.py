"""
automation/portals/registry.py

Helios Portal Registry.
Maps target companies to ATS adapters (Workday, Lever, Greenhouse, Ashby, Taleo).
"""
from typing import Dict, Any, Optional

PORTAL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "siemens": {
        "company_name": "Siemens",
        "ats_type": "workday",
        "login_url": "https://jobs.siemens.com/careers",
        "search_url": "https://jobs.siemens.com/jobs"
    },
    "cred": {
        "company_name": "CRED",
        "ats_type": "lever",
        "login_url": "https://jobs.lever.co/cred",
        "search_url": "https://jobs.lever.co/cred"
    },
    "postman": {
        "company_name": "Postman",
        "ats_type": "greenhouse",
        "login_url": "https://boards.greenhouse.io/postman",
        "search_url": "https://boards.greenhouse.io/postman"
    },
    "razorpay": {
        "company_name": "Razorpay",
        "ats_type": "lever",
        "login_url": "https://jobs.lever.co/razorpay",
        "search_url": "https://jobs.lever.co/razorpay"
    },
    "swiggy": {
        "company_name": "Swiggy",
        "ats_type": "greenhouse",
        "login_url": "https://boards.greenhouse.io/swiggy",
        "search_url": "https://boards.greenhouse.io/swiggy"
    }
}


class PortalRegistry:
    @staticmethod
    def get_config(company: str) -> Optional[Dict[str, Any]]:
        key = company.lower().strip()
        return PORTAL_REGISTRY.get(key)

    @staticmethod
    def register(company: str, ats_type: str, login_url: str, search_url: str):
        key = company.lower().strip()
        PORTAL_REGISTRY[key] = {
            "company_name": company,
            "ats_type": ats_type,
            "login_url": login_url,
            "search_url": search_url
        }

    @staticmethod
    def list_portals() -> list:
        return list(PORTAL_REGISTRY.keys())
