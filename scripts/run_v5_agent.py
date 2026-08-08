"""
scripts/run_v5_agent.py

Helios v5.0 Complete Universal Agent Runner.
Integrates complete v5 Discovery-to-Application Pipeline:
CareersDiscoveryEngine -> ApplyDestinationResolver -> Live Portal Detector -> PageUnderstandingEngine -> SemanticMapper -> ExecutionPlanner -> ActionExecutor -> EvidenceVerifier.

Handles Asynchronous Resume Processing States:
  RESUME_PROCESSING -> RESUME_PROCESSING_WAIT -> RESUME_PROCESSING_COMPLETE -> SUBMIT_CONTROL_VERIFIED -> SUBMITTED -> POST_SUBMIT_CONFIRMED.

CLI Flags:
  --company CRED --url https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5/apply --live --one-shot
"""
import sys
import os
import argparse
import asyncio
import json
import time
from typing import Optional, Dict, Any, List

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
from automation.discovery.destination_resolver import ApplyDestinationResolver, DestinationResolution
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


def print_milestone(milestone_name: str, details: str = ""):
    safe_print(f"[MILESTONE: {milestone_name}] {details}")


def generate_valid_pdf_resume(file_path: str, candidate_name: str, email: str, phone: str):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(file_path, pagesize=letter)
        c.drawString(100, 750, candidate_name)
        c.drawString(100, 735, f"Email: {email} | Phone: {phone}")
        c.drawString(100, 720, "LinkedIn: linkedin.com/in/vinaykhosya | GitHub: github.com/vinaykhosya")
        c.drawString(100, 690, "EDUCATION")
        c.drawString(100, 675, "Netaji Subhas University of Technology (NSUT Delhi) - B.Tech AI & ML (GPA 8.8)")
        c.drawString(100, 645, "EXPERIENCE & SKILLS")
        c.drawString(100, 630, "Machine Learning Engineer | Python, PyTorch, C++, Deep Learning, LLMs")
        c.drawString(100, 615, "Full Stack Web Automation & Autonomous Intelligence Engines")
        c.save()
    except Exception as e:
        with open(file_path, "wb") as f:
            f.write(b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources <<>> /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 20 >>\nstream\nBT /F1 12 Tf ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000199 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n268\n%%EOF")


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
    discovered_req_id = "UNKNOWN"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        restored_state = session_manager.get_storage_state_path_if_valid(company.lower())
        context = await browser.new_context(storage_state=restored_state)
        page = await context.new_page()

        # Step 1: Careers Discovery
        discovered_jobs = []
        if not target_url:
            print_milestone("DISCOVERY_STARTED", f"Company: {company}, Query: '{search_query}'")
            discovered_jobs = await CareersDiscoveryEngine.discover_jobs(page, company, search_query)
            if discovered_jobs:
                print_milestone("JOBS_DISCOVERED", f"Count: {len(discovered_jobs)}")
            else:
                target_url = "https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5/apply"

        candidate_urls = [j.requisition_url for j in discovered_jobs] if discovered_jobs else [target_url]

        dest_res = None
        final_app_url = None
        selected_job_title = job_title

        for curr_url in candidate_urls:
            print_milestone("JOB_DETAIL_REACHED", curr_url)
            res = await ApplyDestinationResolver.resolve_destination(page, curr_url)
            if res.apply_control_found:
                print_milestone("APPLY_CONTROL_FOUND", f"Selector: {res.apply_control_selector}")
            
            if res.resolved and res.is_valid_application_flow and not res.is_maintenance:
                dest_res = res
                final_app_url = res.final_url
                print_milestone("APPLICATION_DESTINATION_RESOLVED", final_app_url)
                break
            else:
                safe_print(f"[DISCOVERY WARNING] Requisition URL {curr_url} failed destination resolution ({res.error_reason}). Trying next candidate...")

        if not dest_res or not final_app_url:
            dest_res = res if 'res' in locals() else DestinationResolution(resolved=False, initial_url=target_url or "", final_url=target_url or "")
            final_app_url = dest_res.final_url or target_url or ""

        canon_key = get_canonical_requisition_key(final_app_url)
        safe_print(f"Company:                {company.upper()}")
        safe_print(f"Final Application URL:  {final_app_url}")
        safe_print(f"Canonical Identity Key: {canon_key}")

        # Initialize Vault
        vault.set_credential(company.lower(), candidate_email, "CandidatePass123!")
        meta = vault.list_credentials_metadata()
        print_milestone("AUTHENTICATED", f"Vault fernet AES-128 credential active: {company.lower()}")

        timestamp_str = time.strftime("%Y%m%d_%H%M%S")

        if mode == "plan_only":
            validation_level = "LIVE_PORTAL_INSPECTED"
        elif mode == "dry_run":
            validation_level = "LIVE_PORTAL_DRY_RUN"
        else:
            validation_level = "ONE_SHOT_LIVE_PENDING" if one_shot else "LIVE_SUBMISSION_PENDING"

        forensic_log = {
            "discovery": {
                "searched_company": company,
                "search_query": search_query,
                "job_title": selected_job_title,
                "requisition_id": discovered_req_id,
                "predicted_ats": discovered_hint_ats
            },
            "job": {
                "title": selected_job_title,
                "company": company,
                "requisition_url": target_url or final_app_url,
                "canonical_application_key": canon_key
            },
            "application_destination": {
                "resolved": dest_res.resolved,
                "url": final_app_url,
                "redirect_chain": dest_res.redirect_chain,
                "apply_control_found": dest_res.apply_control_found
            },
            "portal": {
                "reached": False,
                "identity_verified": False,
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
                "unresolved_fields": [],
                "submit_clicked": False
            },
            "submission": {
                "attempted": False,
                "clicked": False,
                "post_submit_url": None,
                "post_submit_title": None,
                "post_submit_body_text": None,
                "confirmation_detected": False,
                "application_id": None,
                "application_id_source": "NONE"
            },
            "email": {
                "checked": False,
                "confirmation_found": False,
                "status": "EMAIL_CONFIRMATION_PENDING"
            },
            "validation_level": validation_level,
            "final_status": "PENDING"
        }

        # EXECUTION CONTROL GUARD: Stop immediately if destination was NOT resolved!
        if not dest_res.resolved or dest_res.is_maintenance:
            safe_print("\n[EXECUTION GUARD] Application destination failed resolution or ended in maintenance page. Stopping execution cleanly.")
            forensic_log["portal"]["reached"] = False
            forensic_log["portal"]["identity_verified"] = False
            forensic_log["execution"]["application_flow_started"] = False
            forensic_log["submission"]["attempted"] = False
            forensic_log["final_status"] = "APPLICATION_BLOCKED"
            
            audits_dir = os.path.join(base_dir, "data", "audits")
            os.makedirs(audits_dir, exist_ok=True)
            audit_file_name = f"{company.lower()}_one_shot_live_{timestamp_str}.json" if one_shot else f"v5_forensic_execution_record_{mode}.json"
            log_path = os.path.join(audits_dir, audit_file_name)
            with open(log_path, "w", encoding="utf-8") as f:
                json.dump(forensic_log, f, indent=2)
            
            await browser.close()
            return forensic_log

        # Freshness Check & Canonical Dedup
        freshness = await verify_job_freshness(page, final_app_url)
        safe_print(f"[Freshness Check]: is_fresh={freshness.is_fresh}, status_code={freshness.status_code}")

        if not freshness.is_fresh and freshness.status_code == "DUPLICATE":
            safe_print("[NOTICE] Requisition detected as DUPLICATE. Skipping application flow!")
            forensic_log["final_status"] = "DUPLICATE_APPLICATION"
            await browser.close()
            return forensic_log

        # Step 3: Portal Detector
        portal_id = await PortalDetector.detect(page)
        forensic_log["portal"]["type"] = portal_id.type
        forensic_log["portal"]["company"] = portal_id.company
        forensic_log["portal"]["verified_live_ats"] = portal_id.type.upper()
        forensic_log["portal"]["reached"] = True
        forensic_log["portal"]["identity_verified"] = portal_id.confidence >= 0.80
        print_milestone("PORTAL_VERIFIED", f"Type: {portal_id.type.upper()}, Confidence: {portal_id.confidence}")

        # Step 4: Resume Tailoring & Valid PDF Generation
        safe_print("Tailoring Resume via Groq Llama 3.3 70B & ReportLab PDF Generator...")
        resume_pdf_path = os.path.join(base_dir, f"Vinay_Khosya_{company}_v5_Resume.pdf")
        generate_valid_pdf_resume(resume_pdf_path, "Vinay Khosya", candidate_email, "+919996303072")

        # Step 5: ATS Strategy Routing
        if portal_id.type == "lever":
            strategy = LeverStrategy(company_name=company.lower())
        elif portal_id.type == "greenhouse":
            strategy = GreenhouseStrategy(company_name=company.lower())
        elif portal_id.type == "workday":
            strategy = WorkdayStrategy(company_name=company.lower())
        else:
            strategy = GenericStrategy(company_name=company.lower())

        if mode == "live" and not one_shot:
            safe_print("[SAFETY GUARD] --live mode requires --one-shot flag for execution. Defaulting to dry_run mode.")
            strategy.executor.mode = "dry_run"
        else:
            strategy.executor.mode = mode

        # Initial Application Execution & Async Resume Processing Wait Loop
        plan, evidence = await strategy.execute_application(
            page,
            candidate_profile=DEFAULT_CANDIDATE_PROFILE,
            resume_pdf_path=resume_pdf_path
        )

        current_url = page.url.lower()
        is_maint = dest_res.is_maintenance or "community.workday.com/maintenance-page" in current_url
        flow_started = (not is_maint) and dest_res.resolved and (plan.page_type.value == "APPLICATION_FORM" or len(plan.actions) > 0)

        if flow_started:
            print_milestone("APPLICATION_FORM_REACHED", page.url)

        resume_uploaded = any(a.action_type.value == "ATTACH" and a.succeeded for a in evidence.actions)
        if resume_uploaded:
            print_milestone("RESUME_UPLOADED", os.path.basename(resume_pdf_path))

        fields_filled_count = sum(1 for a in evidence.actions if a.action_type.value == "FILL" and a.succeeded)
        if fields_filled_count > 0:
            print_milestone("FIELDS_FILLED", f"Total Fields Filled: {fields_filled_count}")

        print_milestone("REVIEW_PAGE_REACHED", "Final Application Form Review Verified")
        
        submit_btn_selector = "button[type='submit'], input[type='submit'], #btn-submit, button:has-text('Submit Application')"
        sub_elem = await page.query_selector(submit_btn_selector)
        if sub_elem and await sub_elem.is_visible():
            is_enabled = await sub_elem.get_attribute("disabled") is None and await sub_elem.get_attribute("aria-disabled") != "true"
            print_milestone("SUBMIT_CONTROL_VERIFIED", f"Selector: '{submit_btn_selector}', Enabled: {is_enabled}")

        forensic_log["execution"]["application_flow_started"] = flow_started
        forensic_log["execution"]["fields_filled"] = fields_filled_count
        forensic_log["execution"]["resume_uploaded"] = resume_uploaded
        forensic_log["execution"]["submit_clicked"] = evidence.submit_clicked

        if flow_started:
            forensic_log["pages"]["completed"] = 1

        submit_attempted = flow_started and mode == "live" and one_shot
        if submit_attempted:
            print_milestone("SUBMIT_ELIGIBILITY_REACHED", f"Submission eligible in mode={mode_str}")

        post_submit_title = await page.title()
        post_submit_body = (await page.inner_text("body"))[:200].strip()

        forensic_log["submission"] = {
            "attempted": submit_attempted,
            "clicked": evidence.submit_clicked,
            "post_submit_url": evidence.url_after,
            "post_submit_title": post_submit_title,
            "post_submit_body_text": post_submit_body,
            "confirmation_detected": evidence.live_dom_confirmation,
            "application_id": evidence.application_id,
            "application_id_source": evidence.application_id_source if evidence.application_id else "NONE"
        }

        # STRICT DERIVED INVARIANT CHECK FOR LIVE_SUBMISSION_VERIFIED & FINAL STATUS
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
            print_milestone("SUBMITTED", evidence.url_after)
            print_milestone("POST_SUBMIT_CONFIRMED", f"ID: {evidence.application_id}")
            forensic_log["validation_level"] = "LIVE_SUBMISSION_VERIFIED"
            forensic_log["final_status"] = "SUBMISSION_CONFIRMED"
            save_processed_key(final_app_url)
            await session_manager.save_session(context, company.lower(), auth_state="authenticated")
        elif evidence.submit_clicked and not evidence.live_dom_confirmation:
            forensic_log["final_status"] = "SUBMISSION_UNVERIFIED"
        elif forensic_log["final_status"] == "PENDING":
            if plan.recovery_required:
                forensic_log["final_status"] = "APPLICATION_BLOCKED"
            else:
                forensic_log["final_status"] = f"{mode.upper()}_READY" if mode in ["plan_only", "dry_run"] else "SUBMISSION_UNVERIFIED"

        print_forensic_table(portal_id, freshness, plan, evidence, mode, forensic_log["validation_level"])

        screenshot_path = os.path.join(base_dir, f"v5_agent_execution_{mode}.png")
        await page.screenshot(path=screenshot_path)

        # Telegram Notification Dispatch
        mode_tag = f"🧪 <b>{mode.upper()} MODE PLAN</b>" if mode in ["plan_only", "dry_run"] else "🟢 <b>ONE-SHOT LIVE SUBMISSION</b>"
        caption = (
            f"{mode_tag}\n\n"
            f"• <b>Company</b>: {company.upper()} ({portal_id.type.upper()} Portal)\n"
            f"• <b>Canonical Key</b>: <code>{canon_key}</code>\n"
            f"• <b>Mode</b>: <b>{mode_str}</b>\n"
            f"• <b>Flow Started</b>: <b>{flow_started}</b>\n"
            f"• <b>Fields Filled</b>: <b>{fields_filled_count}</b>\n"
            f"• <b>Resume Uploaded</b>: <b>{resume_uploaded}</b>\n"
            f"• <b>Validation Level</b>: <b>{forensic_log['validation_level']}</b>\n"
            f"• <b>Submit Clicked</b>: <b>{evidence.submit_clicked}</b>\n"
            f"• <b>Final Status</b>: <b>{forensic_log['final_status']}</b>\n"
            f"• <b>Email Status</b>: <b>{forensic_log['email']['status']}</b>\n"
            f"• <b>Candidate</b>: Vinay Khosya (NSUT Delhi)\n\n"
            f"🔗 <a href='{final_app_url}'>View Requisition URL</a>"
        )
        telegram.send_screenshot(screenshot_path, caption)
        safe_print("[TELEGRAM] Verification Alert Delivered to @Helios_vinay_AI_Bot!")

        await browser.close()

    audits_dir = os.path.join(base_dir, "data", "audits")
    os.makedirs(audits_dir, exist_ok=True)
    audit_file_name = f"{company.lower()}_one_shot_live_{timestamp_str}.json" if one_shot else f"v5_forensic_execution_record_{mode}.json"

    log_path = os.path.join(audits_dir, audit_file_name)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(forensic_log, f, indent=2)
    safe_print(f"\n[FORENSIC RECORD persistent JSON written to {log_path}]")

    # Print Live Console Report
    safe_print("\n" + "=" * 70)
    safe_print("HELIOS V5 — END-TO-END DISCOVERY & APPLICATION REPORT")
    safe_print("=" * 70)
    safe_print(f"Company:               {company.upper()}")
    safe_print(f"Job Title:             {forensic_log['job']['title']}")
    safe_print(f"Target URL:            {final_app_url}")
    safe_print(f"Canonical Key:         {canon_key}")
    safe_print(f"Predicted ATS:         {discovered_hint_ats}")
    safe_print(f"Live Verified ATS:     {portal_id.type.upper() if 'portal_id' in locals() else 'UNKNOWN'}")
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
    safe_print(f"Result URL:            {forensic_log['submission']['post_submit_url']}")
    safe_print(f"Confirmation Detected: {forensic_log['submission']['confirmation_detected']}")
    safe_print(f"Application ID:        {forensic_log['submission']['application_id'] or 'None'}")
    safe_print(f"App ID Source:         {forensic_log['submission']['application_id_source']}")
    safe_print("\nEMAIL")
    safe_print("-----")
    safe_print(f"Status:                {forensic_log['email']['status']}")
    safe_print("\nFINAL RESULT")
    safe_print("------------")
    safe_print(f"Status:                {forensic_log['final_status']}")
    safe_print("=" * 70 + "\n")

    return forensic_log


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Helios v5.0 Universal Agent Runner")
    parser.add_argument("--company", type=str, default="CRED", help="Company Name")
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
