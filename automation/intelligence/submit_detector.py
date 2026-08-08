"""
automation/intelligence/submit_detector.py

Helios v5.0 Semantic Submit Control Detector.
Evaluates candidate submission controls on Playwright pages:
  - Multi-attribute confidence scoring across visible text, ARIA, role, type, data-attributes, and parent context.
  - Distinguishes wizard navigation actions (NEXT, CONTINUE, REVIEW) from final submission controls (SUBMIT).
  - Recursively scans accessible iframes and shadow DOM roots.
  - Returns structured SubmitCandidate objects and precise diagnostic failure root causes when controls are absent.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


SUBMIT_TEXT_KEYWORDS = [
    "submit application", "submit your application", "submit",
    "apply now", "complete application", "finish application", "send application"
]

WIZARD_NAV_KEYWORDS = [
    "next", "continue", "save and continue", "save & continue", "review", "back", "previous"
]


@dataclass
class SubmitCandidate:
    selector: str
    text: str
    role: str
    confidence: float
    visible: bool
    enabled: bool
    disabled_attr: bool
    aria_disabled: bool
    frame_url: Optional[str] = None
    bounding_box: Optional[Dict[str, float]] = None
    reasoning: List[str] = field(default_factory=list)


@dataclass
class SubmitScanResult:
    found: bool
    best_candidate: Optional[SubmitCandidate] = None
    candidates: List[SubmitCandidate] = field(default_factory=list)
    diagnostic_reason: Optional[str] = None


class SubmitControlDetector:
    @classmethod
    async def scan_page(cls, page) -> SubmitScanResult:
        """
        Scans main page DOM and accessible iframes for candidate submit controls.
        Evaluates visibility, enabled status, and semantic confidence score.
        """
        candidates: List[SubmitCandidate] = []

        # 1. Scan Main Page DOM
        main_candidates = await cls._scan_frame(page)
        candidates.extend(main_candidates)

        # 2. Scan Accessible Iframes
        for frame in page.frames:
            if frame != page.main_frame:
                try:
                    frame_candidates = await cls._scan_frame(frame, frame_url=frame.url)
                    candidates.extend(frame_candidates)
                except Exception:
                    pass

        if not candidates:
            # Diagnostic Analysis for Missing Control
            diag_reason = await cls._diagnose_missing_control(page)
            return SubmitScanResult(found=False, candidates=[], diagnostic_reason=diag_reason)

        # Sort by confidence score descending
        candidates.sort(key=lambda c: c.confidence, reverse=True)
        best = candidates[0]

        if best.confidence >= 0.60:
            return SubmitScanResult(found=True, best_candidate=best, candidates=candidates)

        return SubmitScanResult(
            found=False,
            best_candidate=best,
            candidates=candidates,
            diagnostic_reason=f"Best candidate confidence {best.confidence:.2f} below submittable threshold (0.60)"
        )

    @classmethod
    async def _scan_frame(cls, frame_or_page, frame_url: Optional[str] = None) -> List[SubmitCandidate]:
        frame_candidates: List[SubmitCandidate] = []
        selectors = [
            "button", "input[type='submit']", "input[type='button']",
            "a[role='button']", "[role='button']", ".template-btn-submit",
            "a[href*='submit' i]", "button[data-automation-id*='submit' i]"
        ]

        for sel in selectors:
            try:
                elements = await frame_or_page.query_selector_all(sel)
                for elem in elements:
                    if not await elem.is_visible():
                        continue

                    text = (await elem.inner_text()).strip()
                    val = await elem.get_attribute("value") or ""
                    text_clean = (text or val).lower().strip()
                    if not text_clean and not await elem.get_attribute("aria-label"):
                        continue

                    # Reject pure wizard navigation controls
                    if any(wiz in text_clean for wiz in WIZARD_NAV_KEYWORDS) and not any(sub in text_clean for sub in SUBMIT_TEXT_KEYWORDS):
                        continue

                    score = 0.0
                    reasoning: List[str] = []

                    # Text Match Evaluation
                    for kw in SUBMIT_TEXT_KEYWORDS:
                        if kw == text_clean:
                            score += 0.50
                            reasoning.append(f"Exact text match: '{kw}'")
                            break
                        elif kw in text_clean:
                            score += 0.35
                            reasoning.append(f"Substring text match: '{kw}'")
                            break

                    # Role & Type Evaluation
                    btn_type = await elem.get_attribute("type")
                    if btn_type == "submit":
                        score += 0.25
                        reasoning.append("Attribute type='submit'")

                    role = await elem.get_attribute("role") or "button"
                    if role == "button":
                        score += 0.10
                        reasoning.append("Element role='button'")

                    # Attribute Evaluation (data-automation-id, data-testid, aria-label)
                    auto_id = (await elem.get_attribute("data-automation-id") or "").lower()
                    test_id = (await elem.get_attribute("data-testid") or "").lower()
                    aria_lbl = (await elem.get_attribute("aria-label") or "").lower()

                    if "submit" in auto_id or "submit" in test_id or "submit" in aria_lbl:
                        score += 0.25
                        reasoning.append("Submit indicator in data-automation-id/data-testid/aria-label")

                    # Enabled State
                    dis_attr = await elem.get_attribute("disabled") is not None
                    aria_dis = await elem.get_attribute("aria-disabled") == "true"
                    is_enabled = not dis_attr and not aria_dis

                    if not is_enabled:
                        score *= 0.5
                        reasoning.append("Control currently disabled/aria-disabled")

                    box = await elem.bounding_box()

                    cand = SubmitCandidate(
                        selector=sel,
                        text=text or val or aria_lbl,
                        role=role,
                        confidence=min(score, 1.0),
                        visible=True,
                        enabled=is_enabled,
                        disabled_attr=dis_attr,
                        aria_disabled=aria_dis,
                        frame_url=frame_url,
                        bounding_box=box,
                        reasoning=reasoning
                    )
                    frame_candidates.append(cand)
            except Exception:
                pass

        return frame_candidates

    @classmethod
    async def _diagnose_missing_control(cls, page) -> str:
        """
        Analytically determines why the submit control is absent from the DOM.
        """
        try:
            body_text = (await page.inner_text("body")).lower()
            title_text = (await page.title()).lower()

            if "captcha" in body_text or "security check" in title_text:
                return "CAPTCHA_OR_MFA_CHALLENGE_PRESENT"
            if "sign in" in body_text and "password" in body_text and len(body_text) < 1000:
                return "MANDATORY_LOGIN_REQUIRED"
            
            # Check for unresolved wizard step (Next / Continue buttons visible)
            next_btn = await page.query_selector("button:has-text('Next'), button:has-text('Continue')")
            if next_btn and await next_btn.is_visible():
                return "APPLICATION_IN_WIZARD_STEP_NOT_FINAL_REVIEW"

            # Check for required field validation error messages
            error_el = await page.query_selector(".error, .invalid-feedback, [aria-invalid='true']")
            if error_el and await error_el.is_visible():
                return "REQUIRED_FIELDS_VALIDATION_ERROR_PRESENT"

            # Check for async resume parsing state
            if "analyzing resume" in body_text or "uploading..." in body_text:
                return "RESUME_PROCESSING_INCOMPLETE"

            return "SUBMIT_CONTROL_ABSENT_OR_UNRENDERED"
        except Exception as e:
            return f"DIAGNOSTIC_EXCEPTION: {str(e)}"
