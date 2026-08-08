"""
automation/portals/router.py

Helios Portal Router.
Routes job URLs and company names to target ATS adapters (Lever, Greenhouse, Workday).
"""
from typing import Optional, Tuple
from automation.portals.registry import PortalRegistry


class PortalRouter:
    @staticmethod
    def route_url(url: str) -> Tuple[str, str]:
        """Inspects URL to identify ATS vendor type and target company."""
        url_lower = url.lower()

        if "lever.co" in url_lower:
            parts = url_lower.split("lever.co/")
            company = parts[1].split("/")[0] if len(parts) > 1 else "generic"
            return ("lever", company)
        elif "greenhouse.io" in url_lower:
            parts = url_lower.split("greenhouse.io/")
            company = parts[1].split("/")[0] if len(parts) > 1 else "generic"
            return ("greenhouse", company)
        elif "workday" in url_lower or "myworkdayjobs" in url_lower:
            return ("workday", "siemens" if "siemens" in url_lower else "generic")
        elif "ashbyhq.com" in url_lower:
            return ("ashby", "generic")

        return ("generic", "generic")

    @staticmethod
    def route_company(company_name: str) -> Tuple[str, str]:
        config = PortalRegistry.get_config(company_name)
        if config:
            return (config["ats_type"], config["company_name"])
        return ("generic", company_name)
