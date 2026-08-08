"""
automation/intelligence/executor.py

Helios v5.0 Action Executor.
Safely executes PlannedActions (FILL, ATTACH, CHECK, CLICK) with scroll-into-view,
error tracking, enabled status verification, and produces the EvidencePayload contract.
Supports Three-Level Execution Policy: "plan_only" vs "dry_run" vs "live".
"""
import os
import re
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
        # Three-Level Execution Policy: "plan_only" | "dry_run" | "live"
        self.mode = (mode or os.getenv("HELIOS_EXECUTION_MODE", "dry_run")).lower()

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

            # PLAN_ONLY MODE INVARIANT: Skip all DOM modifications!
            if self.mode == "plan_only":
                rec.succeeded = False
                rec.error = "[PLAN_ONLY] Action planned but skipped in plan_only mode"
                action_records.append(rec)
                continue

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
                        # DRY RUN INVARIANT: In dry_run or plan_only mode, NEVER click submit!
                        if self.mode in ["dry_run", "plan_only"]:
                            rec.succeeded = False
                            rec.error = f"[{self.mode.upper()}] Submission action planned but skipped in {self.mode} mode"
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
                            is_disabled = await btn.get_attribute("disabled") is not None or await btn.get_attribute("aria-disabled") == "true"
                            if is_disabled:
                                rec.succeeded = False
                                rec.error = "Submit button is currently disabled by portal"
                                action_records.append(rec)
                                continue

                            await btn.scroll_into_view_if_needed()
                            await btn.click()
                            await page.wait_for_timeout(5000)
                            rec.succeeded = True
                            submit_clicked = True

            except Exception as e:
                rec.succeeded = False
                rec.error = str(e)

            action_records.append(rec)

        url_after = page.url
        body_text = (await page.inner_text("body")).lower()
        url_after_lower = url_after.lower()

        # Robust DOM Confirmation Check
        dom_confirmation = (
            "/thanks" in url_after_lower
            or "confirmation" in url_after_lower
            or "thanks for applying" in body_text
            or "application submitted" in body_text
            or "application received" in body_text
            or "thank you for your application" in body_text
            or "your application has been submitted" in body_text
        )

        live_app_id = None
        if dom_confirmation:
            match = re.search(r'(?:application|req|reference|id)\s*(?:#|id|number)?\s*:?\s*([a-z0-9\-]{6,25})', body_text, re.IGNORECASE)
            if match:
                live_app_id = match.group(1)

        app_id_source = "LIVE_PORTAL_DOM" if live_app_id else "NONE"

        return EvidencePayload(
            submit_clicked=submit_clicked,
            live_dom_confirmation=dom_confirmation,
            application_id=live_app_id,
            application_id_source=app_id_source,
            url_before=url_before,
            url_after=url_after,
            actions=action_records
        )
