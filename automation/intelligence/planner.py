"""
automation/intelligence/planner.py

Helios v5.0 Execution Planner.
Transforms PageSchema contracts into explicit ExecutionPlans via SemanticMapper.
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
from automation.intelligence.semantic_mapper import SemanticMapper, ValueSource
from automation.fillers.semantic_filler import DEFAULT_CANDIDATE_PROFILE


class ExecutionPlanner:
    def __init__(self, candidate_profile: Optional[Dict[str, Any]] = None, verified_memory: Optional[Dict[str, str]] = None):
        self.profile = candidate_profile or DEFAULT_CANDIDATE_PROFILE
        self.mapper = SemanticMapper(self.profile, verified_memory)

    def create_plan(self, schema: PageSchema, resume_pdf_path: Optional[str] = None) -> ExecutionPlan:
        """
        Transforms PageSchema -> SemanticMapping -> ExecutionPlan contract.
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

        # Map Schema via SemanticMapper
        mapping = self.mapper.map_schema(schema)
        actions = []

        # Generate FILL actions from mapped values
        for mapped_val in mapping.mapped_values:
            if mapped_val.value and not mapped_val.recovery_required:
                field_elem = next((f for f in schema.fields if f.element_id == mapped_val.element_id), None)
                if field_elem:
                    actions.append(
                        PlannedAction(
                            action_id=f"act-fill-{mapped_val.semantic.value}",
                            action_type=ActionType.FILL,
                            target_semantic=mapped_val.semantic,
                            target_selector=field_elem.selector_used,
                            value_to_fill=mapped_val.value,
                            confidence=mapped_val.confidence
                        )
                    )

        # Generate ATTACH action for resume
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

        # Generate CLICK action for Submit Button
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
            and mapping.unresolved_count == 0
            and not mapping.requires_human_recovery
        )

        return ExecutionPlan(
            page_type=schema.page_type,
            actions=actions,
            submission_allowed=is_submittable,
            recovery_required=not is_submittable and schema.page_type == PageType.APPLICATION_FORM,
            recovery_reason=RecoveryReason.NONE if is_submittable else (
                RecoveryReason.UNRESOLVED_SENSITIVE_QUESTION if mapping.unresolved_count > 0 else RecoveryReason.SUBMISSION_CONFIDENCE_LOW
            ),
            min_action_confidence=min([a.confidence for a in actions]) if actions else 1.0
        )
