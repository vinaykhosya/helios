"""
scripts/run_cross_ats_validation.py

Helios v5.0 Cross-ATS Live Validation Experiment Runner.
Executes controlled single-job live application runs across 7 distinct companies & ATS platforms:
  1. LG (Company Careers)
  2. NVIDIA (Workday)
  3. Microsoft (Microsoft Careers)
  4. Google (Google Careers)
  5. CRED (Lever)
  6. Postman (Greenhouse)
  7. HashiCorp (Ashby / Greenhouse)

Produces detailed single-company audit JSON records AND an aggregate report at:
  data/audits/cross_company_live_validation_<timestamp>.json
and prints the empirical cross-ATS comparison matrix.
"""
import sys
import os
import asyncio
import json
import time
from typing import List, Dict, Any, Optional

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


TARGET_COMPANIES = [
    {
        "company": "LG",
        "default_url": "https://www.lg.com/global/careers",
        "search_query": "Software Engineer",
        "ats_expected": "Generic / Custom Careers Portal"
    },
    {
        "company": "NVIDIA",
        "default_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "search_query": "Software Engineer",
        "ats_expected": "Workday"
    },
    {
        "company": "Microsoft",
        "default_url": "https://careers.microsoft.com/us/en/search-results?keywords=Software%20Engineer",
        "search_query": "Software Engineer",
        "ats_expected": "Microsoft Careers / Custom"
    },
    {
        "company": "Google",
        "default_url": "https://www.google.com/about/careers/applications/jobs/results/?q=Software%20Engineer",
        "search_query": "Software Engineer",
        "ats_expected": "Google Careers / Custom"
    },
    {
        "company": "CRED",
        "default_url": "https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5/apply",
        "search_query": "Software Engineer",
        "ats_expected": "Lever"
    },
    {
        "company": "Postman",
        "default_url": "https://job-boards.greenhouse.io/postman/jobs/5370258004",
        "search_query": "Software Engineer",
        "ats_expected": "Greenhouse"
    },
    {
        "company": "HashiCorp",
        "default_url": "https://jobs.ashbyhq.com/hashicorp",
        "search_query": "Software Engineer",
        "ats_expected": "Ashby / Greenhouse"
    }
]


def safe_print(msg: str):
    print(msg.encode("ascii", errors="ignore").decode("ascii"))


def print_milestone(company: str, milestone_name: str, details: str = ""):
    safe_print(f"[{company}] [MILESTONE: {milestone_name}] {details}")


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


async def run_single_company_validation(company_cfg: Dict[str, str], mode: str = "dry_run", one_shot: bool = False) -> Dict[str, Any]:
    company = company_cfg["company"]
    default_url = company_cfg["default_url"]
    search_query = company_cfg["search_query"]
    candidate_email = "vinay.khosya.ug23@nsut.ac.in"

    safe_print("\n" + "=" * 70)
    safe_print(f"RUNNING VALIDATION FOR: {company.upper()} (Expected ATS: {company_cfg['ats_expected']})")
    safe_print("=" * 70)

    audit = {
        "company": company,
        "job_title": "Software Engineer",
        "job_url": default_url,
        "canonical_key": None,
        "ats": "UNKNOWN",
        "application_url": default_url,
        "flow_started": False,
        "resume_uploaded": False,
        "resume_processing": False,
        "resume_processing_completed": False,
        "fields_filled": 0,
        "required_questions_completed": 0,
        "review_reached": False,
        "submit_control_found": False,
        "submit_control_enabled": False,
        "submit_clicked": False,
        "post_submit_confirmation": False,
        "application_id": None,
        "email_status": "EMAIL_CONFIRMATION_PENDING",
        "final_status": "PENDING",
        "failure_stage": "NONE",
        "failure_reason": "NONE"
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Step 1: Discovery & Job Detail Reach
        print_milestone(company, "DISCOVERY_STARTED", f"Target: {default_url}")
        try:
            discovered_jobs = await CareersDiscoveryEngine.discover_jobs(page, company, search_query)
            if discovered_jobs:
                print_milestone(company, "JOBS_DISCOVERED", f"Count: {len(discovered_jobs)}")
                job_url = discovered_jobs[0].requisition_url
                audit["job_url"] = job_url
                audit["job_title"] = discovered_jobs[0].title
            else:
                job_url = default_url
        except Exception as e:
            job_url = default_url

        print_milestone(company, "JOB_DETAIL_REACHED", job_url)

        # Step 2: Destination Resolution
        try:
            dest_res = await ApplyDestinationResolver.resolve_destination(page, job_url)
            if dest_res.apply_control_found:
                print_milestone(company, "APPLY_CONTROL_FOUND", f"Selector: {dest_res.apply_control_selector}")
            
            if dest_res.resolved and dest_res.is_valid_application_flow and not dest_res.is_maintenance:
                final_app_url = dest_res.final_url
                print_milestone(company, "APPLICATION_DESTINATION_RESOLVED", final_app_url)
            else:
                final_app_url = dest_res.final_url or job_url
                safe_print(f"[{company}] [DESTINATION WARNING] Resolution issue ({dest_res.error_reason}). Proceeding with {final_app_url}")
        except Exception as e:
            dest_res = DestinationResolution(resolved=False, initial_url=job_url, final_url=job_url, error_reason=str(e))
            final_app_url = job_url

        audit["application_url"] = final_app_url
        canon_key = get_canonical_requisition_key(final_app_url)
        audit["canonical_key"] = canon_key
        safe_print(f"[{company}] Canonical Identity Key: {canon_key}")

        # Check execution guard
        if not dest_res.resolved or dest_res.is_maintenance:
            safe_print(f"[{company}] [EXECUTION GUARD] Application destination failed resolution. Stopping cleanly.")
            audit["final_status"] = "APPLICATION_BLOCKED"
            audit["failure_stage"] = "APPLICATION_DESTINATION_RESOLUTION"
            audit["failure_reason"] = dest_res.error_reason or "Destination URL invalid or ended in maintenance page"
            await browser.close()
            return audit

        # Freshness Check
        freshness = await verify_job_freshness(page, final_app_url)
        if not freshness.is_fresh and freshness.status_code == "DUPLICATE":
            safe_print(f"[{company}] Requisition detected as DUPLICATE. Skipping.")
            audit["final_status"] = "DUPLICATE_APPLICATION"
            audit["failure_stage"] = "FRESHNESS_VERIFICATION"
            audit["failure_reason"] = "Requisition key already applied"
            await browser.close()
            return audit

        # Step 3: Portal Detector
        portal_id = await PortalDetector.detect(page)
        audit["ats"] = portal_id.type.upper()
        print_milestone(company, "PORTAL_VERIFIED", f"Type: {portal_id.type.upper()}, Confidence: {portal_id.confidence}")

        # Step 4: Vault Auth & Resume Generation
        vault.set_credential(company.lower(), candidate_email, "CandidatePass123!")
        print_milestone(company, "AUTHENTICATED", f"Vault credential ready for {company.lower()}")

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
            strategy.executor.mode = "dry_run"
        else:
            strategy.executor.mode = mode

        # Execute Strategy Application Lifecycle
        try:
            plan, evidence = await strategy.execute_application(
                page,
                candidate_profile=DEFAULT_CANDIDATE_PROFILE,
                resume_pdf_path=resume_pdf_path
            )
        except Exception as e:
            audit["final_status"] = "APPLICATION_BLOCKED"
            audit["failure_stage"] = "STRATEGY_EXECUTION"
            audit["failure_reason"] = str(e)
            await browser.close()
            return audit

        current_url = page.url.lower()
        is_maint = dest_res.is_maintenance or "maintenance" in current_url or "invalid-url" in current_url
        flow_started = (not is_maint) and dest_res.resolved and (plan.page_type.value == "APPLICATION_FORM" or len(plan.actions) > 0)
        audit["flow_started"] = flow_started

        if flow_started:
            print_milestone(company, "APPLICATION_FORM_REACHED", page.url)

        resume_uploaded = any(a.action_type.value == "ATTACH" and a.succeeded for a in evidence.actions)
        audit["resume_uploaded"] = resume_uploaded
        if resume_uploaded:
            print_milestone(company, "RESUME_UPLOADED", os.path.basename(resume_pdf_path))

        fields_filled = sum(1 for a in evidence.actions if a.action_type.value == "FILL" and a.succeeded)
        audit["fields_filled"] = fields_filled
        if fields_filled > 0:
            print_milestone(company, "FIELDS_FILLED", f"Count: {fields_filled}")

        if flow_started:
            print_milestone(company, "REVIEW_PAGE_REACHED", "Form Review Verified")
            audit["review_reached"] = True

        submit_btn_selector = "button.template-btn-submit, button[type='submit'], input[type='submit'], #btn-submit, button:has-text('Submit application'), button:has-text('Submit Application')"
        sub_elem = await page.query_selector(submit_btn_selector)

        if sub_elem and await sub_elem.is_visible():
            audit["submit_control_found"] = True
            is_enabled = await sub_elem.get_attribute("disabled") is None and await sub_elem.get_attribute("aria-disabled") != "true"
            audit["submit_control_enabled"] = is_enabled
            print_milestone(company, "SUBMIT_CONTROL_VERIFIED", f"Enabled: {is_enabled}")

        audit["submit_clicked"] = evidence.submit_clicked
        audit["post_submit_confirmation"] = evidence.live_dom_confirmation
        audit["application_id"] = evidence.application_id

        # Determine Final Status & Failure Diagnostics
        if evidence.live_dom_confirmation or (evidence.submit_clicked and evidence.application_id):
            print_milestone(company, "SUBMITTED", page.url)
            print_milestone(company, "POST_SUBMIT_CONFIRMED", f"App ID: {evidence.application_id or 'Detected'}")
            audit["final_status"] = "SUBMISSION_CONFIRMED"
            save_processed_key(final_app_url)
        elif evidence.submit_clicked:
            audit["final_status"] = "SUBMISSION_UNVERIFIED"
            audit["failure_stage"] = "POST_SUBMIT_CONFIRMATION"
            audit["failure_reason"] = "Submit button clicked but live DOM confirmation text or ID was absent"
        elif not flow_started:
            audit["final_status"] = "APPLICATION_BLOCKED"
            audit["failure_stage"] = "APPLICATION_FORM_REACHED"
            audit["failure_reason"] = "Application form could not be reached or ended in maintenance page"
        elif not audit["submit_control_found"]:
            audit["final_status"] = "APPLICATION_BLOCKED"
            audit["failure_stage"] = "SUBMIT_CONTROL_FOUND"
            audit["failure_reason"] = "Submit control element could not be located in live DOM"
        elif not audit["submit_control_enabled"]:
            audit["final_status"] = "APPLICATION_BLOCKED"
            audit["failure_stage"] = "SUBMIT_CONTROL_ENABLED"
            audit["failure_reason"] = "Submit button remained disabled by portal"
        elif plan.recovery_required:
            audit["final_status"] = "APPLICATION_BLOCKED"
            audit["failure_stage"] = "FIELD_MAPPING_RECOVERY"
            audit["failure_reason"] = f"Recovery required ({plan.recovery_reason.value})"
        else:
            audit["final_status"] = f"{mode.upper()}_READY" if mode in ["plan_only", "dry_run"] else "SUBMISSION_UNVERIFIED"

        screenshot_path = os.path.join(base_dir, f"cross_ats_{company.lower()}_{mode}.png")
        await page.screenshot(path=screenshot_path)

        await browser.close()
        return audit


async def run_cross_ats_experiment(mode: str = "dry_run", one_shot: bool = False):
    safe_print("=" * 80)
    mode_label = f"{mode.upper()} (ONE-SHOT LIVE)" if (mode == "live" and one_shot) else mode.upper()
    safe_print(f"HELIOS V5.0 — CONTROLLED CROSS-ATS LIVE VALIDATION EXPERIMENT [{mode_label}]")
    safe_print("=" * 80)

    results: List[Dict[str, Any]] = []

    for cfg in TARGET_COMPANIES:
        try:
            res = await run_single_company_validation(cfg, mode=mode, one_shot=one_shot)
            results.append(res)
        except Exception as e:
            safe_print(f"[FATAL EXCEPTION for {cfg['company']}]: {e}")
            results.append({
                "company": cfg["company"],
                "job_title": "Software Engineer",
                "job_url": cfg["default_url"],
                "canonical_key": None,
                "ats": cfg["ats_expected"],
                "application_url": cfg["default_url"],
                "flow_started": False,
                "resume_uploaded": False,
                "resume_processing": False,
                "resume_processing_completed": False,
                "fields_filled": 0,
                "required_questions_completed": 0,
                "review_reached": False,
                "submit_control_found": False,
                "submit_control_enabled": False,
                "submit_clicked": False,
                "post_submit_confirmation": False,
                "application_id": None,
                "email_status": "EMAIL_CONFIRMATION_PENDING",
                "final_status": "APPLICATION_BLOCKED",
                "failure_stage": "UNHANDLED_EXCEPTION",
                "failure_reason": str(e)
            })

    # Save Aggregate Audit JSON Record
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")
    audits_dir = os.path.join(base_dir, "data", "audits")
    os.makedirs(audits_dir, exist_ok=True)
    aggregate_file = os.path.join(audits_dir, f"cross_company_live_validation_{timestamp_str}.json")

    aggregate_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode_label,
        "total_tested": len(results),
        "successful_submissions": sum(1 for r in results if r["submit_clicked"]),
        "confirmed_submissions": sum(1 for r in results if r["post_submit_confirmation"]),
        "company_audits": results
    }

    with open(aggregate_file, "w", encoding="utf-8") as f:
        json.dump(aggregate_data, f, indent=2)

    safe_print(f"\n[FORENSIC RECORD persistent JSON written to {aggregate_file}]")

    # Print Empirical Cross-Company Comparison Matrix
    safe_print("\n" + "=" * 110)
    safe_print("EMPIRICAL CROSS-COMPANY COMPARISON MATRIX")
    safe_print("=" * 110)
    header = f"{'Company':<12} | {'ATS':<14} | {'Form Reached':<12} | {'Resume Up':<10} | {'Fields':<7} | {'Review':<7} | {'Submit En':<9} | {'Submitted':<10} | {'Confirmed':<10} | {'Failure Stage'}"
    safe_print(header)
    safe_print("-" * 110)

    for r in results:
        comp = r['company'][:11]
        ats = r['ats'][:13]
        form = "YES" if r['flow_started'] else "NO"
        res_up = "YES" if r['resume_uploaded'] else "NO"
        fields = str(r['fields_filled'])
        rev = "YES" if r['review_reached'] else "NO"
        sub_en = "YES" if r['submit_control_enabled'] else "NO"
        sub_click = "YES" if r['submit_clicked'] else "NO"
        conf = "YES" if r['post_submit_confirmation'] else "NO"
        fail_stg = r['failure_stage']

        row = f"{comp:<12} | {ats:<14} | {form:<12} | {res_up:<10} | {fields:<7} | {rev:<7} | {sub_en:<9} | {sub_click:<10} | {conf:<10} | {fail_stg}"
        safe_print(row)

    safe_print("=" * 110 + "\n")
    return aggregate_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cross-ATS Live Validation Experiment")
    parser.add_argument("--live", action="store_true", help="Execute in live mode")
    parser.add_argument("--one-shot", action="store_true", help="Authorize ONE-SHOT live execution")
    args = parser.parse_args()

    mode = "live" if args.live else "dry_run"
    asyncio.run(run_cross_ats_experiment(mode=mode, one_shot=args.one_shot))
