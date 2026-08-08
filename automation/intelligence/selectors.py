"""
automation/intelligence/selectors.py

Helios v5.0 8-Priority Selector Hierarchy Resolver.
Locates DOM elements resiliently across heterogeneous career portals (Workday, Lever, Greenhouse, custom React).
Follows priority order P1 -> P7 before falling back to Recovery Queue (P8).
"""
from typing import Optional, Tuple, Any, List
from automation.intelligence.contracts import ElementSemantic

SEMANTIC_PATTERNS = {
    ElementSemantic.FIRST_NAME: {
        "autocomplete": ["given-name", "fname", "first-name"],
        "names": ["first_name", "firstname", "first-name", "fname", "job_application[first_name]"],
        "ats_ids": ["first_name", "givenname", "legalname-first", "#first_name"],
        "aria": ["first name", "given name", "first"],
        "labels": ["first name", "given name", "legal first name"],
        "placeholders": ["first name", "given name", "john"]
    },
    ElementSemantic.LAST_NAME: {
        "autocomplete": ["family-name", "lname", "last-name"],
        "names": ["last_name", "lastname", "last-name", "lname", "job_application[last_name]"],
        "ats_ids": ["last_name", "familyname", "legalname-last", "#last_name"],
        "aria": ["last name", "family name", "surname"],
        "labels": ["last name", "family name", "surname", "legal last name"],
        "placeholders": ["last name", "family name", "doe"]
    },
    ElementSemantic.EMAIL: {
        "autocomplete": ["email"],
        "names": ["email", "email_address", "applicant_email", "job_application[email]"],
        "ats_ids": ["email", "emailaddress", "#email"],
        "aria": ["email", "email address"],
        "labels": ["email", "email address"],
        "placeholders": ["email", "example@domain.com"]
    },
    ElementSemantic.PHONE: {
        "autocomplete": ["tel", "phone"],
        "names": ["phone", "telephone", "mobile", "phone_number", "job_application[phone]"],
        "ats_ids": ["phone", "phonenumber", "mobile", "#phone"],
        "aria": ["phone", "telephone", "mobile number"],
        "labels": ["phone", "telephone", "phone number", "mobile"],
        "placeholders": ["phone", "+91", "mobile"]
    },
    ElementSemantic.ORGANIZATION: {
        "autocomplete": ["organization"],
        "names": ["org", "company", "organization", "current_company", "job_application[company]"],
        "ats_ids": ["org", "company", "school", "institution", "#org"],
        "aria": ["company", "organization", "university", "school"],
        "labels": ["company", "organization", "current company", "university"],
        "placeholders": ["company", "organization", "university"]
    },
    ElementSemantic.LINKEDIN: {
        "autocomplete": ["url"],
        "names": ["linkedin", "urls[linkedin]", "urls_linkedin", "job_application[answers_attributes][0][text_value]"],
        "ats_ids": ["linkedin"],
        "aria": ["linkedin", "linkedin profile", "linkedin url"],
        "labels": ["linkedin", "linkedin profile", "linkedin url"],
        "placeholders": ["linkedin.com/in/"]
    },
    ElementSemantic.GITHUB: {
        "autocomplete": ["url"],
        "names": ["github", "urls[github]", "urls_github"],
        "ats_ids": ["github"],
        "aria": ["github", "github profile", "github url"],
        "labels": ["github", "github profile", "github url"],
        "placeholders": ["github.com/"]
    }
}


class SelectorResolver:
    @staticmethod
    async def locate_element(page, semantic: ElementSemantic) -> Optional[Tuple[Any, str, float]]:
        """
        Locates Playwright ElementHandle using 8-Priority Hierarchy.
        Returns: (ElementHandle, css_selector_string, confidence_score) or None
        """
        patterns = SEMANTIC_PATTERNS.get(semantic)
        if not patterns:
            return None

        # Priority 1: Autocomplete attribute (Confidence: 0.99)
        for auto in patterns.get("autocomplete", []):
            sel = f"input[autocomplete='{auto}']"
            elem = await SelectorResolver._try_query(page, sel)
            if elem:
                return (elem, sel, 0.99)

        # Priority 2: Direct ID / Name attribute (Confidence: 0.98)
        for name in patterns.get("names", []):
            sel = f"input#{name}, input[name='{name}'], input[name*='{name}']"
            elem = await SelectorResolver._try_query(page, sel)
            if elem:
                return (elem, sel, 0.98)

        # Priority 3: ATS Vendor data-automation-id / data-qa / ID (Confidence: 0.97)
        for ats_id in patterns.get("ats_ids", []):
            sel = f"input#{ats_id.replace('#', '')}, input[data-automation-id*='{ats_id}'], input[data-qa*='{ats_id}']"
            elem = await SelectorResolver._try_query(page, sel)
            if elem:
                return (elem, sel, 0.97)

        # Priority 4: ARIA Label (Confidence: 0.95)
        for aria in patterns.get("aria", []):
            sel = f"input[aria-label*='{aria}' i], textarea[aria-label*='{aria}' i]"
            elem = await SelectorResolver._try_query(page, sel)
            if elem:
                return (elem, sel, 0.95)

        # Priority 5: Associated Label text (Confidence: 0.92)
        for label_text in patterns.get("labels", []):
            sel = f"label:has-text('{label_text}') + input, label:has-text('{label_text}') input"
            elem = await SelectorResolver._try_query(page, sel)
            if elem:
                return (elem, sel, 0.92)

        # Priority 6: Placeholder text (Confidence: 0.90)
        for ph in patterns.get("placeholders", []):
            sel = f"input[placeholder*='{ph}' i]"
            elem = await SelectorResolver._try_query(page, sel)
            if elem:
                return (elem, sel, 0.90)

        # Priority 7/8: Unresolvable via P1-P6 -> Return None to trigger Recovery Queue
        return None

    @staticmethod
    async def _try_query(page, selector: str) -> Optional[Any]:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                return elem
        except Exception:
            pass
        return None
