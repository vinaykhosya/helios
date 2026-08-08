"""
scripts/run_v5_agent.py

Helios v5.0 Complete Universal Agent Runner.
Integrates the complete v5 Universal Portal Intelligence Pipeline:
Canonical ApplicationKey Dedup -> PortalDetector -> PageUnderstandingEngine -> SemanticMapper -> ExecutionPlanner -> ActionExecutor -> EvidenceVerifier.

Enforces 4-Level Audit Hierarchy:
  1. UNIT_TEST: Mocked unit test execution
  2. LIVE_PORTAL_INSPECTED: Real portal reached & analyzed in plan_only mode
  3. LIVE_PORTAL_DRY_RUN: Real portal fields/actions executed, submit blocked in dry_run mode
  4. LIVE_SUBMISSION_VERIFIED: Real submit occurred + live DOM confirmation obtained in live mode

CLI Flags:
  --company CRED --url <requisition_url> [--plan-only | --dry-run | --live]
  Default execution policy is DRY RUN (--dry-run).
"""
import sys
import os
import argparse
import asyncio
import json
import time

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright
from backend.src.services.resume_service import ResumeService
from backend.src.services.telegram_service import TelegramService

from automation.sessions.credentials import EncryptedCredentialVault
from automation.sessions.manager import PortalSessionManager
from automation.verifier import verify_job_freshness, get_canonical_requisition_key, save_processed_key
from automation.portals.detector import PortalDetector
from automation.portals.strategies.lever import LeverStrategy
from automation.portals.strategies.greenhouse import GreenhouseStrategy
from automation.portals.strategies.workday import WorkdayStrategy
from automation.portals.strategies.generic import GenericStrategy
from automation.fillers.semantic_filler import DEFAULT_CANDIDATE_PROFILE

telegram = TelegramService()
resume_service = ResumeService(template_path="templates/master_resume.tex")
session_manager = PortalSessionManager()
vault = EncryptedCredentialVault()


def safe_print(msg: str):
    print(msg.encode("ascii", errors="ignore").decode("ascii"))


def print_forensic_table(portal_id, freshness, plan, evidence, mode, validation_level):
    safe_print("\n" + "─" * 60)
    safe_print("PAGE UNDERSTANDING & SCHEMA")
    safe_print("─" * 60)
    safe_print(f"Validation Level:     {validation_level}")
    safe_print(f"Portal Type:          {portal_id.type.upper()}")
    safe_print(f"Company Tenant:       {portal_id.company.upper()}")
    safe_print(f"Freshness Status:     {freshness.status_code}")
    safe_print(f"Page Type:            {plan.page_type.value}")

    safe_print("\n" + "─" * 60)
    safe_print("EXECUTION PLAN ACTIONS")
    safe_print("─" * 60)
    safe_print(f"Total Actions:        {len(plan.actions)}")
    for act in plan.actions:
        safe_print(f"  [{act.action_type.value}] {act.target_semantic.value:<20} -> {act.target_selector}")

    safe_print("\n" + "─" * 60)
    safe_print("EXECUTION POLICY & SAFETY BOUNDARIES")
    safe_print("─" * 60)
    safe_print(f"Policy Mode:          {mode.upper()}")
    safe_print(f"Submission Allowed:   {plan.submission_allowed}")
    safe_print(f"Recovery Required:    {plan.recovery_required}")
    safe_print(f"Recovery Reason:      {plan.recovery_reason.value}")

    safe_print("\n" + "─" * 60)
    safe_print("FORENSIC EVIDENCE & VERIFICATION RESULT")
    safe_print("─" * 60)
    safe_print(f"Submit Clicked:       {evidence.submit_clicked}")
    safe_print(f"DOM Confirmation:     {evidence.live_dom_confirmation}")
    safe_print(f"Application ID:       {evidence.application_id or 'None'}")
    safe_print(f"App ID Source:        {evidence.application_id_source}")
    safe_print("─" * 60 + "\n")


async def run_v5_pipeline(company: str, target_url: str, mode: str = "dry_run"):
    safe_print("=" * 70)
    safe_print(f"[HELIOS v5.0] UNIVERSAL AGENT RUNNER — MODE: {mode.upper()}")
    safe_print("=" * 70)

    candidate_email = "vinay.khosya.ug23@nsut.ac.in"
    canon_key = get_canonical_requisition_key(target_url)
    safe_print(f"Target URL: {target_url}")
    safe_print(f"Canonical Identity Key: {canon_key}")

    # Determine initial validation level
    if mode == "plan_only":
        validation_level = "LIVE_PORTAL_INSPECTED"
    elif mode == "dry_run":
        validation_level = "LIVE_PORTAL_DRY_RUN"
    else:
        validation_level = "LIVE_SUBMISSION_PENDING"

    # Step 1: Encrypt Credentials in Vault
    vault.set_credential(company.lower(), candidate_email, "CandidatePass123!")
    meta = vault.list_credentials_metadata()
    safe_print(f"[Step 1] Vault Credentials Initialized (Fernet AES-128): {meta}")

    forensic_log = {
        "canonical_application_key": canon_key,
        "company": company,
        "target_url": target_url,
        "mode": mode,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "validation_level": validation_level,
        "live_portal_verified": False,
        "portal_identity": None,
        "freshness_check": None,
        "execution_plan": None,
        "evidence_payload": None,
        "final_status": "PENDING"
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Restore storageState session if available
        restored_state = session_manager.get_storage_state_path_if_valid(company.lower())
        context = await browser.new_context(storage_state=restored_state)
        page = await context.new_page()

        safe_print("\n[Step 2] Navigating Requisition URL...")
        await page.goto(target_url, timeout=15000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        # Freshness Check
        freshness = await verify_job_freshness(page, target_url)
        forensic_log["freshness_check"] = {
            "is_fresh": freshness.is_fresh,
            "status_code": freshness.status_code,
            "reason": freshness.reason
        }
        safe_print(f"[Step 2] Freshness Check: is_fresh={freshness.is_fresh}, status_code={freshness.status_code}")

        if not freshness.is_fresh and freshness.status_code == "DUPLICATE":
            safe_print("[NOTICE] Requisition detected as DUPLICATE. Skipping application flow!")
            forensic_log["final_status"] = "SKIPPED_DUPLICATE"
            await browser.close()
            return forensic_log

        # Step 3: Portal Detector
        portal_id = await PortalDetector.detect(page)
        forensic_log["portal_identity"] = {
            "type": portal_id.type,
            "company": portal_id.company,
            "confidence": portal_id.confidence
        }
        safe_print(f"[Step 3] Portal Detector: type='{portal_id.type}', company='{portal_id.company}', confidence={portal_id.confidence}")

        # Step 4: Resume Tailoring
        safe_print("Tailoring Resume via Groq Llama 3.3 70B...")
        tailored = await resume_service.tailor_resume("Machine Learning Engineer", company, "Python, PyTorch, Deep Learning")
        resume_pdf_path = os.path.join(base_dir, f"Vinay_Khosya_{company}_v5_Resume.pdf")
        with open(resume_pdf_path, "w", encoding="utf-8") as f:
            f.write("% PDF Binary\n" + tailored.get("tailored_tex", ""))

        # Step 5: ATS Strategy Routing (Lever vs Greenhouse vs Workday vs Generic)
        if portal_id.type == "lever":
            strategy = LeverStrategy(company_name=company.lower())
        elif portal_id.type == "greenhouse":
            strategy = GreenhouseStrategy(company_name=company.lower())
        elif portal_id.type == "workday":
            strategy = WorkdayStrategy(company_name=company.lower())
        else:
            strategy = GenericStrategy(company_name=company.lower())

        # Set execution policy mode on ActionExecutor inside strategy
        strategy.executor.mode = mode

        plan, evidence = await strategy.execute_application(
            page,
            candidate_profile=DEFAULT_CANDIDATE_PROFILE,
            resume_pdf_path=resume_pdf_path
        )

        forensic_log["execution_plan"] = plan.to_dict()
        forensic_log["evidence_payload"] = {
            "submit_clicked": evidence.submit_clicked,
            "live_dom_confirmation": evidence.live_dom_confirmation,
            "application_id": evidence.application_id,
            "application_id_source": evidence.application_id_source,
            "url_before": evidence.url_before,
            "url_after": evidence.url_after,
            "actions_executed": [
                {
                    "action_id": a.action_id,
                    "action_type": a.action_type.value,
                    "target_semantic": a.target_semantic.value,
                    "succeeded": a.succeeded,
                    "error": a.error
                }
                for a in evidence.actions
            ]
        }

        # Step 6: Final Status Determination & Validation Hierarchy Enforcement
        if evidence.is_strong_evidence() and mode == "live":
            forensic_log["validation_level"] = "LIVE_SUBMISSION_VERIFIED"
            forensic_log["live_portal_verified"] = True
            forensic_log["final_status"] = "CONFIRMED_APPLIED"
            save_processed_key(target_url)
            await session_manager.save_session(context, company.lower(), auth_state="authenticated")
        elif plan.recovery_required:
            forensic_log["final_status"] = "RECOVERY_REQUIRED"
        else:
            forensic_log["final_status"] = f"{mode.upper()}_READY" if mode in ["plan_only", "dry_run"] else "SUBMISSION_UNVERIFIED"

        print_forensic_table(portal_id, freshness, plan, evidence, mode, forensic_log["validation_level"])

        screenshot_path = os.path.join(base_dir, f"v5_agent_execution_{mode}.png")
        await page.screenshot(path=screenshot_path)

        # Step 7: Telegram Notification Dispatch
        mode_tag = f"🧪 <b>{mode.upper()} MODE PLAN</b>" if mode in ["plan_only", "dry_run"] else "🟢 <b>LIVE SUBMISSION</b>"
        caption = (
            f"{mode_tag}\n\n"
            f"• <b>Company</b>: {company.upper()} ({portal_id.type.upper()} Portal)\n"
            f"• <b>Canonical Key</b>: <code>{canon_key}</code>\n"
            f"• <b>Mode</b>: <b>{mode.upper()}</b>\n"
            f"• <b>Validation Level</b>: <b>{forensic_log['validation_level']}</b>\n"
            f"• <b>Planned Actions</b>: {len(plan.actions)}\n"
            f"• <b>Submit Clicked</b>: <b>{evidence.submit_clicked}</b>\n"
            f"• <b>Final Status</b>: <b>{forensic_log['final_status']}</b>\n"
            f"• <b>Recovery Required</b>: <b>{plan.recovery_required}</b>\n"
            f"• <b>Candidate</b>: Vinay Khosya (NSUT Delhi)\n\n"
            f"🔗 <a href='{target_url}'>View Requisition URL</a>"
        )
        telegram.send_screenshot(screenshot_path, caption)
        safe_print("[TELEGRAM] Verification Alert Delivered to @Helios_vinay_AI_Bot!")

        await browser.close()

    log_path = os.path.join(base_dir, f"v5_forensic_execution_record_{mode}.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(forensic_log, f, indent=2)
    safe_print(f"[FORENSIC RECORD persistent JSON written to {log_path}]")

    safe_print("\n" + "=" * 70)
    safe_print(f"[SUCCESS] HELIOS v5.0 PIPELINE EXECUTION COMPLETED ({mode.upper()})!")
    safe_print("=" * 70)
    return forensic_log


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Helios v5.0 Universal Agent Runner")
    parser.add_argument("--company", type=str, default="CRED", help="Company Name")
    parser.add_argument("--url", type=str, default="https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5", help="Requisition URL")
    parser.add_argument("--plan-only", action="store_true", help="Execute plan-only mode (no DOM changes)")
    parser.add_argument("--live", action="store_true", help="Execute live submission mode")

    args = parser.parse_args()
    if args.plan_only:
        exec_mode = "plan_only"
    elif args.live:
        exec_mode = "live"
    else:
        exec_mode = "dry_run"

    asyncio.run(run_v5_pipeline(args.company, args.url, mode=exec_mode))
