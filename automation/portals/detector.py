"""
automation/portals/detector.py

Helios v5.0 Automatic Portal Detector.
Detects ATS type and company tenant automatically from URL and DOM attributes.
Emits PortalIdentity dataclass.
"""
import urllib.parse
from dataclasses import dataclass


@dataclass
class PortalIdentity:
    type: str         # "workday" | "lever" | "greenhouse" | "ashby" | "generic"
    company: str      # e.g. "cred", "postman", "siemens"
    confidence: float # 0.0 - 1.0


class PortalDetector:
    @staticmethod
    async def detect(page) -> PortalIdentity:
        """
        Detects ATS type and company tenant identity from Playwright page.
        """
        url = page.url.lower()
        parsed = urllib.parse.urlparse(url)
        netloc = parsed.netloc
        path = parsed.path.rstrip("/").lower()

        # Lever Detection
        if "lever.co" in netloc:
            parts = [p for p in path.split("/") if p]
            comp = parts[0] if parts else "unknown"
            return PortalIdentity(type="lever", company=comp, confidence=0.99)

        # Greenhouse Detection
        if "greenhouse.io" in netloc:
            parts = [p for p in path.split("/") if p]
            comp = parts[0] if parts else "unknown"
            return PortalIdentity(type="greenhouse", company=comp, confidence=0.99)

        # Workday Detection
        if "myworkdayjobs.com" in netloc or "workday" in netloc:
            comp = netloc.split(".")[0].replace("-careers", "").replace("_careers", "")
            return PortalIdentity(type="workday", company=comp, confidence=0.99)

        # Ashby Detection
        if "ashbyhq.com" in netloc:
            parts = [p for p in path.split("/") if p]
            comp = parts[0] if parts else "unknown"
            return PortalIdentity(type="ashby", company=comp, confidence=0.99)

        # Generic Portal Fallback Strategy
        domain_parts = netloc.split(".")
        comp = domain_parts[-2] if len(domain_parts) >= 2 else "unknown"
        return PortalIdentity(type="generic", company=comp, confidence=0.80)
