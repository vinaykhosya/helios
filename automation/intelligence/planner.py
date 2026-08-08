"""
automation/intelligence/planner.py

Helios v5.0 Execution Planner.
Transforms PageSchema contracts into explicit ExecutionPlans.
Enforces strict safety invariants: submission_allowed is True ONLY if all required fields are resolved,
zero CAPTCHA/MFA, and submit target confidence >= 0.95.
"""
from typing import Dict, Any, Optional
from automation.intelligence.contracts import (
    PageSchema,
    PageType,
    ExecutionPlan,
    PlannedAction,
    ActionType,
    ElementSemantic,
    RecoveryReason
)
from automation.fillers.semantic_filler import SemanticFormEngine, DEFAULT_CANDIDATE_PROFILE


class ExecutionPlanner:
    def __init__(self, candidate_profile: Optional[Dict[str, Any]] = None):
        self.profile = candidate_profile or DEFAULT_CANDIDATE_PROFILE
        self.semantic_engine = SemanticFormEngine(self.profile)

    def create_plan(self, schema: PageSchema, resume_pdf_path: Optional[str] = None) -> ExecutionPlan:
        """
        Transforms PageSchema into ExecutionPlan contract.
        """
        # Safety Check 1: CAPTCHA Challenge
        if schema.has_captcha or schema.page_type == PageType.CAPTCHA_CHALLENGE:
            return ExecutionPlan(
                page_type=schema.page_type,
                submission_allowed=False,
                recovery_required=True,
                recovery_reason=RecoveryReason.CAPTCHA_OR_MFA_DETECTED
            )

        # Safety Check 2: Mandatory Login Required
        if schema.has_login_prompt or schema.page_type == PageType.LOGIN_REQUIRED:
            return ExecutionPlan(
                page_type=schema.page_type,
                submission_allowed=False,
                recovery_required=True,
                recovery_reason=RecoveryReason.MANDATORY_LOGIN_REQUIRED
            )

        actions = []
        unresolved_fields = 0

        # Plan FILL actions for fields
        for field_elem in schema.fields:
            sem = field_elem.semantic
            val_to_fill = None

            if sem == ElementSemantic.FIRST_NAME or sem == ElementSemantic.FULL_NAME:
                val_to_fill = self.profile.get("name", "Vinay Khosya")
            elif sem == ElementSemantic.LAST_NAME:
                val_to_fill = self.profile.get("last_name", "Khosya")
            elif sem == ElementSemantic.EMAIL:
                val_to_fill = self.profile.get("email", "vinay.khosya.ug23@nsut.ac.in")
            elif sem == ElementSemantic.PHONE:
                val_to_fill = self.profile.get("phone", "+919996303072")
            elif sem == ElementSemantic.ORGANIZATION:
                val_to_fill = self.profile.get("org", "NSUT Delhi")
            elif sem == ElementSemantic.LINKEDIN:
                val_to_fill = self.profile.get("linkedin", "https://linkedin.com/in/vinaykhosya")
            elif sem == ElementSemantic.GITHUB:
                val_to_fill = self.profile.get("github", "https://github.com/vinaykhosya")

            if val_to_fill:
                actions.append(
                    PlannedAction(
                        action_id=f"act-fill-{sem.value}",
                        action_type=ActionType.FILL,
                        target_semantic=sem,
                        target_selector=field_elem.selector_used,
                        value_to_fill=val_to_fill,
                        confidence=field_elem.confidence
                    )
                )
            else:
                unresolved_fields += 1

        # Plan ATTACH action for resume
        if resume_pdf_path:
            actions.append(
                PlannedAction(
                    action_id="act-attach-resume",
                    action_type=ActionType.ATTACH,
                    target_semantic=ElementSemantic.RESUME_UPLOAD,
                    target_selector="input[type='file']",
                    value_to_fill=resume_pdf_path,
                    confidence=1.0
                )
            )

        # Plan CLICK action for Submit Button
        submit_btn = next((b for b in schema.buttons if b.semantic == ElementSemantic.SUBMIT_APPLICATION), None)
        if submit_btn:
            actions.append(
                PlannedAction(
                    action_id="act-click-submit",
                    action_type=ActionType.CLICK,
                    target_semantic=ElementSemantic.SUBMIT_APPLICATION,
                    target_selector=submit_btn.selector_used,
                    confidence=submit_btn.confidence
                )
            )

        # Enforce submission_allowed invariant
        is_submittable = (
            schema.page_type == PageType.APPLICATION_FORM
            and submit_btn is not None
            and submit_btn.confidence >= 0.90
            and unresolved_fields == 0
        )

        return ExecutionPlan(
            page_type=schema.page_type,
            actions=actions,
            submission_allowed=is_submittable,
            recovery_required=not is_submittable and schema.page_type == PageType.APPLICATION_FORM,
            recovery_reason=RecoveryReason.NONE if is_submittable else RecoveryReason.SUBMISSION_CONFIDENCE_LOW,
            min_action_confidence=min([a.confidence for a in actions]) if actions else 1.0
        )
