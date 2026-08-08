"""
automation/intelligence/executor.py

Helios v5.0 Action Executor.
Safely executes PlannedActions (FILL, ATTACH, CHECK, CLICK) with scroll-into-view,
error tracking, and produces the EvidencePayload contract.
Supports execution_mode="dry_run" (plans & fills fields, but NEVER clicks submit).
"""
import os
from typing import List, Optional
from automation.intelligence.contracts import (
    ExecutionPlan,
    ActionType,
    ElementSemantic,
    ActionExecution,
    EvidencePayload
)


class ActionExecutor:
    def __init__(self, mode: Optional[str] = None):
        # execution_mode can be set via constructor or HELIOS_EXECUTION_MODE env var ("dry_run" vs "live")
        self.mode = mode or os.getenv("HELIOS_EXECUTION_MODE", "live").lower()

    async def execute_plan(self, page, plan: ExecutionPlan) -> EvidencePayload:
        """
        Executes actions in ExecutionPlan and returns EvidencePayload contract.
        """
        url_before = page.url
        action_records: List[ActionExecution] = []
        submit_clicked = False

        for action in plan.actions:
            rec = ActionExecution(
                action_id=action.action_id,
                action_type=action.action_type,
                target_semantic=action.target_semantic,
                target_selector=action.target_selector,
                attempted=True,
                succeeded=False
            )

            try:
                if action.action_type == ActionType.FILL:
                    elem = await page.query_selector(action.target_selector)
                    if elem and await elem.is_visible():
                        await page.fill(action.target_selector, action.value_to_fill or "")
                        rec.succeeded = True

                elif action.action_type == ActionType.ATTACH:
                    file_inputs = await page.query_selector_all("input[type='file']")
                    if file_inputs:
                        await file_inputs[0].set_input_files(action.value_to_fill)
                        rec.succeeded = True

                elif action.action_type == ActionType.CLICK:
                    if action.target_semantic == ElementSemantic.SUBMIT_APPLICATION:
                        # DRY RUN INVARIANT: In dry_run mode, NEVER click submit!
                        if self.mode == "dry_run":
                            rec.succeeded = False
                            rec.error = "[DRY_RUN] Submission action planned but skipped in dry-run mode"
                            action_records.append(rec)
                            continue

                        # Safety rule: Only click submit if submission_allowed is True
                        if not plan.submission_allowed:
                            rec.succeeded = False
                            rec.error = "Submission disallowed by ExecutionPlan safety policy"
                            action_records.append(rec)
                            continue

                        btn = await page.query_selector(action.target_selector)
                        if btn and await btn.is_visible():
                            await btn.scroll_into_view_if_needed()
                            await btn.click()
                            await page.wait_for_timeout(4000)
                            rec.succeeded = True
                            submit_clicked = True

            except Exception as e:
                rec.succeeded = False
                rec.error = str(e)

            action_records.append(rec)

        url_after = page.url
        body_text = (await page.inner_text("body")).lower()
        url_after_lower = url_after.lower()

        # DOM Confirmation Check
        dom_confirmation = (
            "/thanks" in url_after_lower
            or "thanks for applying" in body_text
            or "application submitted" in body_text
            or "application received" in body_text
        )

        live_app_id = None
        if "/thanks" in url_after_lower:
            parts = url_after_lower.split("/")
            for p in parts:
                if len(p) > 10 and "-" in p:
                    live_app_id = p

        return EvidencePayload(
            submit_clicked=submit_clicked,
            live_dom_confirmation=dom_confirmation,
            application_id=live_app_id,
            application_id_source="LIVE_PORTAL_DOM" if live_app_id else ("NONE" if not submit_clicked else "DOM_TEXT"),
            url_before=url_before,
            url_after=url_after,
            actions=action_records
        )
