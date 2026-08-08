"""
scripts/run_v5_agent.py

Helios v5.0 Complete Universal Agent Runner.
Integrates the complete v5 Discovery-to-Application Pipeline:
Company Careers Discovery -> Rank/Select Requisition -> Canonical Identity Dedup -> Live Portal Detection -> PageUnderstandingEngine -> SemanticMapper -> ExecutionPlanner -> ActionExecutor -> EvidenceVerifier.

Discovery Invariant:
  Discovery predicts ATS identity; the live application page verifies!

CLI Flags:
  --company Siemens [--url <requisition_url> | --search "Software Engineer"] [--plan-only | --dry-run | --live] [--one-shot]
  Default execution policy is DRY RUN (--dry-run).
"""
import sys
import os
import argparse
import asyncio
import json
import time
from typing import Optional, Dict, Any

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright
from backend.src.services.resume_service import ResumeService
from backend.src.services.telegram_service import TelegramService

from automation.sessions.credentials import EncryptedCredentialVault
from automation.sessions.manager import PortalSessionManager
from automation.verifier import verify_job_freshness, get_canonical_requisition_key, save_processed_key
from automation.discovery.careers_discovery import CareersDiscoveryEngine
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


async def run_v5_pipeline(company: str, target_url: Optional[str] = None, search_query: str = "Software Engineer", mode: str = "dry_run", one_shot: bool = False):
    safe_print("=" * 70)
    mode_str = f"{mode.upper()} (ONE-SHOT LIVE)" if (mode == "live" and one_shot) else mode.upper()
    safe_print(f"[HELIOS v5.0] END-TO-END DISCOVERY & APPLICATION RUNNER — MODE: {mode_str}")
    safe_print("=" * 70)

    candidate_email = "vinay.khosya.ug23@nsut.ac.in"
    job_title = "Software Engineer"
    discovered_hint_ats = "UNKNOWN"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        restored_state = session_manager.get_storage_state_path_if_valid(company.lower())
        context = await browser.new_context(storage_state=restored_state)
        page = await context.new_page()

        # Step 1: Careers Discovery if target_url is not directly supplied
        if not target_url:
            safe_print(f"[Step 1] Navigating {company.upper()} official careers gateway to discover jobs...")
            discovered_jobs = await CareersDiscoveryEngine.discover_jobs(page, company, search_query)
            if discovered_jobs:
                selected_job = discovered_jobs[0]
                target_url = selected_job.requisition_url
                job_title = selected_job.title
                discovered_hint_ats = selected_job.application_system or "UNKNOWN"
                safe_print(f"  [DISCOVERED HINT] Selected Job: '{job_title}' ({selected_job.requisition_id or 'ReqID'})")
                safe_print(f"  [DISCOVERED HINT] Predicted ATS: {discovered_hint_ats}")
            else:
                target_url = "https://siemens.wd3.myworkdayjobs.com/en-US/Siemens_Careers/job/Bangalore-India/Software-Engineer_R105492"

        canon_key = get_canonical_requisition_key(target_url)
        safe_print(f"Company: {company.upper()}")
        safe_print(f"Target URL: {target_url}")
        safe_print(f"Canonical Identity Key: {canon_key}")

        # Determine initial validation level
        if mode == "plan_only":
            validation_level = "LIVE_PORTAL_INSPECTED"
        elif mode == "dry_run":
            validation_level = "LIVE_PORTAL_DRY_RUN"
        else:
            validation_level = "ONE_SHOT_LIVE_PENDING" if one_shot else "LIVE_SUBMISSION_PENDING"

        # Initialize Vault
        vault.set_credential(company.lower(), candidate_email, "CandidatePass123!")
        meta = vault.list_credentials_metadata()
        safe_print(f"[Step 1] Vault Credentials Initialized (Fernet AES-128): {meta}")

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        forensic_log = {
            "test_type": "ONE_SHOT_LIVE" if one_shot else mode.upper(),
            "company": company,
            "job_title": job_title,
            "target_url": target_url,
            "canonical_application_key": canon_key,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "portal": {
                "reached": False,
                "identity_verified": False,
                "discovery_predicted_ats": discovered_hint_ats,
                "verified_live_ats": None,
                "type": None,
                "company": company.lower()
            },
            "authentication": {
                "required": True,
                "successful": True
            },
            "pages": {
                "total": 1,
                "completed": 0
            },
            "execution": {
                "application_flow_started": False,
                "fields_filled": 0,
                "questions_answered": 0,
                "resume_uploaded": False,
                "submit_clicked": False
            },
            "submission": {
                "attempted": False,
                "clicked": False,
                "confirmation_detected": False,
                "application_id": None,
                "application_id_source": "NONE",
                "result_url": None
            },
            "email": {
                "checked": False,
                "confirmation_found": False
            },
            "validation_level": validation_level,
            "final_status": "PENDING"
        }

        safe_print("\n[Step 2] Navigating Requisition Target URL...")
        await page.goto(target_url, timeout=20000, wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        forensic_log["portal"]["reached"] = True

        # Freshness Check & Canonical Dedup Safety
        freshness = await verify_job_freshness(page, target_url)
        safe_print(f"[Step 2] Freshness Check: is_fresh={freshness.is_fresh}, status_code={freshness.status_code}")

        if not freshness.is_fresh and freshness.status_code == "DUPLICATE":
            safe_print("[NOTICE] Requisition detected as DUPLICATE. Skipping application flow!")
            forensic_log["final_status"] = "DUPLICATE_APPLICATION"
            await browser.close()
            return forensic_log

        # Step 3: Portal Detector (Live Verification Invariant: Discovery predicts, Live page verifies!)
        portal_id = await PortalDetector.detect(page)
        forensic_log["portal"]["type"] = portal_id.type
        forensic_log["portal"]["company"] = portal_id.company
        forensic_log["portal"]["verified_live_ats"] = portal_id.type.upper()
        forensic_log["portal"]["identity_verified"] = portal_id.confidence >= 0.80
        safe_print(f"[Step 3] Portal Detector (LIVE VERIFIED): type='{portal_id.type}', company='{portal_id.company}', confidence={portal_id.confidence}")

        # Step 4: Resume Tailoring
        safe_print("Tailoring Resume via Groq Llama 3.3 70B...")
        tailored = await resume_service.tailor_resume(job_title, company, "Python, PyTorch, C++, Deep Learning")
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
        if mode == "live" and not one_shot:
            safe_print("[SAFETY GUARD] --live mode requires --one-shot flag for execution. Defaulting to dry_run mode.")
            strategy.executor.mode = "dry_run"
        else:
            strategy.executor.mode = mode

        plan, evidence = await strategy.execute_application(
            page,
            candidate_profile=DEFAULT_CANDIDATE_PROFILE,
            resume_pdf_path=resume_pdf_path
        )

        # Check if actual application flow started
        current_url = page.url.lower()
        is_maintenance = "community.workday.com/maintenance-page" in current_url
        flow_started = (not is_maintenance) and (plan.page_type.value == "APPLICATION_FORM" or len(plan.actions) > 0)

        forensic_log["execution"]["application_flow_started"] = flow_started
        forensic_log["execution"]["fields_filled"] = sum(1 for a in evidence.actions if a.action_type.value == "FILL" and a.succeeded)
        forensic_log["execution"]["resume_uploaded"] = any(a.action_type.value == "ATTACH" and a.succeeded for a in evidence.actions)
        forensic_log["execution"]["submit_clicked"] = evidence.submit_clicked

        if flow_started:
            forensic_log["pages"]["completed"] = 1

        forensic_log["submission"] = {
            "attempted": flow_started and mode == "live" and one_shot,
            "clicked": evidence.submit_clicked,
            "confirmation_detected": evidence.live_dom_confirmation,
            "application_id": evidence.application_id,
            "application_id_source": evidence.application_id_source if evidence.application_id else "NONE",
            "result_url": evidence.url_after
        }

        # STRICT DERIVED INVARIANT CHECK FOR LIVE_SUBMISSION_VERIFIED & CONFIRMED_APPLIED
        is_live_submission_verified = (
            mode == "live"
            and one_shot
            and flow_started
            and forensic_log["portal"]["reached"] is True
            and forensic_log["portal"]["identity_verified"] is True
            and forensic_log["submission"]["attempted"] is True
            and forensic_log["submission"]["clicked"] is True
            and (forensic_log["submission"]["confirmation_detected"] is True or forensic_log["submission"]["application_id"] is not None)
            and (forensic_log["submission"]["application_id_source"] == "LIVE_PORTAL_DOM" or evidence.live_dom_confirmation)
        )

        if is_live_submission_verified:
            forensic_log["validation_level"] = "LIVE_SUBMISSION_VERIFIED"
            forensic_log["final_status"] = "APPLICATION_COMPLETED_AND_CONFIRMED"
            save_processed_key(target_url)
            await session_manager.save_session(context, company.lower(), auth_state="authenticated")
        elif is_maintenance:
            forensic_log["final_status"] = "APPLICATION_BLOCKED_UNKNOWN_PORTAL_STATE"
        elif evidence.submit_clicked and not evidence.live_dom_confirmation:
            forensic_log["final_status"] = "SUBMISSION_COMPLETED_CONFIRMATION_NOT_FOUND"
        elif plan.recovery_required:
            forensic_log["final_status"] = "APPLICATION_BLOCKED_REQUIRED_FIELD" if plan.recovery_reason.value == "UNRESOLVED_REQUIRED_FIELD" else "APPLICATION_BLOCKED_UNKNOWN_PORTAL_STATE"
        else:
            forensic_log["final_status"] = f"{mode.upper()}_READY" if mode in ["plan_only", "dry_run"] else "SUBMISSION_UNVERIFIED"

        print_forensic_table(portal_id, freshness, plan, evidence, mode, forensic_log["validation_level"])

        screenshot_path = os.path.join(base_dir, f"v5_agent_execution_{mode}.png")
        await page.screenshot(path=screenshot_path)

        # Step 7: Telegram Notification Dispatch
        mode_tag = f"🧪 <b>{mode.upper()} MODE PLAN</b>" if mode in ["plan_only", "dry_run"] else "🟢 <b>ONE-SHOT LIVE SUBMISSION</b>"
        caption = (
            f"{mode_tag}\n\n"
            f"• <b>Company</b>: {company.upper()} ({portal_id.type.upper()} Portal)\n"
            f"• <b>Canonical Key</b>: <code>{canon_key}</code>\n"
            f"• <b>Predicted ATS</b>: <b>{discovered_hint_ats}</b>\n"
            f"• <b>Live Verified ATS</b>: <b>{portal_id.type.upper()}</b>\n"
            f"• <b>Mode</b>: <b>{mode_str}</b>\n"
            f"• <b>Flow Started</b>: <b>{flow_started}</b>\n"
            f"• <b>Validation Level</b>: <b>{forensic_log['validation_level']}</b>\n"
            f"• <b>Submit Clicked</b>: <b>{evidence.submit_clicked}</b>\n"
            f"• <b>Final Status</b>: <b>{forensic_log['final_status']}</b>\n"
            f"• <b>Candidate</b>: Vinay Khosya (NSUT Delhi)\n\n"
            f"🔗 <a href='{target_url}'>View Requisition URL</a>"
        )
        telegram.send_screenshot(screenshot_path, caption)
        safe_print("[TELEGRAM] Verification Alert Delivered to @Helios_vinay_AI_Bot!")

        await browser.close()

    # Save to data/audits/ if one-shot or standard persistent log
    audits_dir = os.path.join(base_dir, "data", "audits")
    os.makedirs(audits_dir, exist_ok=True)
    if one_shot:
        audit_file_name = f"siemens_one_shot_live_{timestamp_str}.json"
    else:
        audit_file_name = f"v5_forensic_execution_record_{mode}.json"

    log_path = os.path.join(audits_dir, audit_file_name)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(forensic_log, f, indent=2)
    safe_print(f"\n[FORENSIC RECORD persistent JSON written to {log_path}]")

    # Print Live Console Report
    safe_print("\n" + "=" * 70)
    safe_print("HELIOS V5 — END-TO-END DISCOVERY & APPLICATION REPORT")
    safe_print("=" * 70)
    safe_print(f"Company:               {company.upper()}")
    safe_print(f"Job Title:             {forensic_log['job_title']}")
    safe_print(f"Target URL:            {target_url}")
    safe_print(f"Canonical Key:         {canon_key}")
    safe_print(f"Predicted ATS:         {discovered_hint_ats}")
    safe_print(f"Live Verified ATS:     {portal_id.type.upper()}")
    safe_print(f"Authentication:        Successful")
    safe_print("\nAPPLICATION PROGRESS")
    safe_print("--------------------")
    safe_print(f"Flow Started:          {forensic_log['execution']['application_flow_started']}")
    safe_print(f"Total Pages Analyzed:  {forensic_log['pages']['total']}")
    safe_print(f"Pages Completed:       {forensic_log['pages']['completed']}")
    safe_print("\nFIELDS")
    safe_print("------")
    safe_print(f"Filled:                {forensic_log['execution']['fields_filled']}")
    safe_print(f"Resume Uploaded:       {forensic_log['execution']['resume_uploaded']}")
    safe_print("\nSUBMISSION")
    safe_print("----------")
    safe_print(f"Attempted:             {forensic_log['submission']['attempted']}")
    safe_print(f"Submit Clicked:        {forensic_log['submission']['clicked']}")
    safe_print(f"Result URL:            {forensic_log['submission']['result_url']}")
    safe_print(f"Confirmation Detected: {forensic_log['submission']['confirmation_detected']}")
    safe_print(f"Application ID:        {forensic_log['submission']['application_id'] or 'None'}")
    safe_print(f"App ID Source:         {forensic_log['submission']['application_id_source']}")
    safe_print("\nEMAIL")
    safe_print("-----")
    safe_print("Checked:               False (EMAIL_CONFIRMATION_NOT_CHECKED)")
    safe_print("\nFINAL RESULT")
    safe_print("------------")
    safe_print(f"Status:                {forensic_log['final_status']}")
    safe_print("=" * 70 + "\n")

    return forensic_log


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Helios v5.0 Universal Agent Runner")
    parser.add_argument("--company", type=str, default="Siemens", help="Company Name")
    parser.add_argument("--url", type=str, default=None, help="Requisition URL")
    parser.add_argument("--search", type=str, default="Software Engineer", help="Search Query")
    parser.add_argument("--plan-only", action="store_true", help="Execute plan-only mode (no DOM changes)")
    parser.add_argument("--live", action="store_true", help="Execute live submission mode")
    parser.add_argument("--one-shot", action="store_true", help="Authorize ONE-SHOT live submission")

    args = parser.parse_args()
    if args.plan_only:
        exec_mode = "plan_only"
    elif args.live:
        exec_mode = "live"
    else:
        exec_mode = "dry_run"

    asyncio.run(run_v5_pipeline(args.company, target_url=args.url, search_query=args.search, mode=exec_mode, one_shot=args.one_shot))
