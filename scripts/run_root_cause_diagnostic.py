"""
scripts/run_root_cause_diagnostic.py

Helios v5.0 — Final Root-Cause Diagnostic Runner.
Read-only instrumentation: does NOT modify portal strategies, executor, or submission logic.
Traces the complete state machine across fresh job requisitions.
Produces:
  data/diagnostics/root_cause/root_cause_report_<timestamp>.json
  data/diagnostics/root_cause/<run_id>/  (per-company DOM forensics)
"""
import sys
import os
import asyncio
import json
import time
import datetime
from typing import List, Dict, Any, Optional

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

from playwright.async_api import async_playwright, Page
from automation.discovery.destination_resolver import ApplyDestinationResolver, DestinationResolution
from automation.portals.detector import PortalDetector
from automation.intelligence.submit_detector import SubmitControlDetector
from automation.verifier import get_canonical_requisition_key, load_processed_keys
from automation.fillers.semantic_filler import DEFAULT_CANDIDATE_PROFILE

# ─────────────────────────────────────────────────────────────────────────────
# FRESH DIAGNOSTIC TARGETS  (none previously applied)
# ─────────────────────────────────────────────────────────────────────────────
DIAGNOSTIC_TARGETS = [
    {
        "company": "NVIDIA",
        "job_title": "Senior System Software Engineer",
        "job_url": "https://jobs.nvidia.com/careers/job/893392590814",
        "ats_expected": "GENERIC/NVIDIA",
        "notes": "Modal flow: Apply Now → Upload Resume → Continue → submit"
    },
    {
        "company": "Lever_Fresh",
        "job_title": "Backend Engineer",
        "job_url": "https://jobs.lever.co/verkada/d28553b2-1a07-4378-bbcc-3bc73c98ab71/apply",
        "ats_expected": "LEVER",
        "notes": "Fresh Lever job (Verkada) — not previously applied"
    },
    {
        "company": "Greenhouse_Fresh",
        "job_title": "Software Engineer",
        "job_url": "https://boards.greenhouse.io/gitlab/jobs/7955695002",
        "ats_expected": "GREENHOUSE",
        "notes": "Fresh Greenhouse job (GitLab) — not previously applied"
    },
    {
        "company": "Workday_Fresh",
        "job_title": "Software Engineer",
        "job_url": "https://amazon.jobs/en/jobs/2932921/software-dev-engineer",
        "ats_expected": "WORKDAY/AMAZON",
        "notes": "Amazon fresh requisition — test destination resolution"
    }
]

FAILURE_KINDS = [
    "NETWORK_FAILURE", "DNS_FAILURE", "TLS_FAILURE", "BROWSER_FAILURE",
    "BOT_PROTECTION", "CAPTCHA", "AUTHENTICATION_FAILURE", "JOB_NOT_FOUND",
    "CLOSED_JOB", "APPLICATION_DESTINATION_FAILURE", "FORM_DETECTION_FAILURE",
    "FIELD_MAPPING_FAILURE", "RESUME_UPLOAD_FAILURE", "RESUME_PROCESSING_FAILURE",
    "REVIEW_DETECTION_FAILURE", "SUBMIT_DETECTION_FAILURE", "SUBMIT_DISABLED",
    "SUBMISSION_FAILURE", "POST_SUBMIT_VERIFICATION_FAILURE", "DUPLICATE_APPLICATION",
    "HUMAN_ACTION_REQUIRED_CAPTCHA"
]


def sp(msg: str):
    print(msg.encode("ascii", errors="ignore").decode("ascii"))


def ts() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_valid_pdf(path: str):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas as rc
        c = rc.Canvas(path, pagesize=letter)
        c.drawString(100, 750, "Vinay Khosya")
        c.drawString(100, 735, "Email: vinay.khosya.ug23@nsut.ac.in | Phone: +919996303072")
        c.drawString(100, 720, "LinkedIn: linkedin.com/in/vinaykhosya | GitHub: github.com/vinaykhosya")
        c.drawString(100, 695, "EDUCATION")
        c.drawString(100, 680, "NSUT Delhi - B.Tech AI & ML (GPA 8.8)")
        c.drawString(100, 660, "EXPERIENCE")
        c.drawString(100, 645, "Machine Learning Engineer | Python, PyTorch, C++, Deep Learning, LLMs")
        c.save()
    except Exception:
        with open(path, "wb") as f:
            f.write(b"%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
                    b"2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n"
                    b"3 0 obj\n<</Type/Page/Parent 2 0 R>>\nendobj\nxref\n0 4\n"
                    b"0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n"
                    b"0000000115 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n158\n%%EOF")


async def dom_forensics(page: Page, company: str, milestone: str, run_dir: str) -> Dict[str, Any]:
    """Capture full DOM forensic snapshot and screenshot."""
    try:
        body_text = await page.inner_text("body")
        title = await page.title()
        current_url = page.url
    except Exception as e:
        return {"error": str(e)}

    controls = []
    try:
        for sel in ["button", "input", "textarea", "select",
                    "a[role='button']", "[role='button']"]:
            elems = await page.query_selector_all(sel)
            for el in elems[:30]:
                try:
                    vis = await el.is_visible()
                    tag = await el.evaluate("e => e.tagName.toLowerCase()")
                    txt = (await el.inner_text()).strip()[:80]
                    val = await el.get_attribute("value") or ""
                    el_type = await el.get_attribute("type") or ""
                    role = await el.get_attribute("role") or ""
                    aria_lbl = await el.get_attribute("aria-label") or ""
                    name = await el.get_attribute("name") or ""
                    el_id = await el.get_attribute("id") or ""
                    cls = (await el.get_attribute("class") or "")[:60]
                    auto_id = await el.get_attribute("data-automation-id") or ""
                    test_id = await el.get_attribute("data-testid") or ""
                    data_qa = await el.get_attribute("data-qa") or ""
                    disabled = await el.get_attribute("disabled") is not None
                    aria_dis = await el.get_attribute("aria-disabled") == "true"
                    href = await el.get_attribute("href") or ""
                    box = await el.bounding_box()
                    controls.append({
                        "sel": sel, "tag": tag, "text": txt or val or aria_lbl,
                        "type": el_type, "role": role, "aria_label": aria_lbl,
                        "name": name, "id": el_id, "classes": cls,
                        "data_automation_id": auto_id, "data_testid": test_id,
                        "data_qa": data_qa, "disabled": disabled, "aria_disabled": aria_dis,
                        "href": href[:80], "visible": vis, "bounding_box": box
                    })
                except Exception:
                    pass
    except Exception:
        pass

    iframes = []
    try:
        for frame in page.frames:
            iframes.append({"name": frame.name, "url": frame.url})
    except Exception:
        pass

    # Detect CAPTCHA
    captcha_detected = False
    captcha_iframe_url = ""
    captcha_type = ""
    try:
        for f in page.frames:
            if "recaptcha" in f.url or "captcha" in f.url or "hcaptcha" in f.url:
                captcha_detected = True
                captcha_iframe_url = f.url
                captcha_type = "recaptcha" if "recaptcha" in f.url else "hcaptcha"
                break
        if "captcha" in body_text.lower() or "security check" in title.lower():
            captcha_detected = True
            captcha_type = captcha_type or "inline"
    except Exception:
        pass

    screenshot_path = os.path.join(run_dir, f"{company}_{milestone}.png")
    try:
        await page.screenshot(path=screenshot_path)
    except Exception:
        screenshot_path = None

    return {
        "timestamp": ts(),
        "url": current_url,
        "page_title": title,
        "body_text_length": len(body_text),
        "body_text_snippet": body_text[:1500],
        "total_controls": len(controls),
        "controls": controls,
        "iframes": iframes,
        "captcha_detected": captcha_detected,
        "captcha_type": captcha_type,
        "captcha_iframe_url": captcha_iframe_url,
        "screenshot": screenshot_path
    }


async def run_single_diagnostic(target: Dict, run_dir: str) -> Dict[str, Any]:
    company = target["company"]
    job_url = target["job_url"]
    sp(f"\n{'='*70}")
    sp(f"DIAGNOSTIC: {company.upper()} | {target['ats_expected']}")
    sp(f"URL: {job_url}")
    sp(f"{'='*70}")

    milestones: Dict[str, Any] = {}
    result = {
        "company": company,
        "job_title": target["job_title"],
        "job_url": job_url,
        "ats_expected": target["ats_expected"],
        "ats_detected": "UNKNOWN",
        "canonical_key": None,
        "milestones": milestones,
        "failure_kind": "NONE",
        "failure_reason": "NONE",
        "final_status": "PENDING",
        "dom_snapshots": {}
    }

    def record(name: str, **kwargs):
        milestones[name] = {"timestamp": ts(), "url": "", **kwargs}
        sp(f"  [{company}] MILESTONE: {name}")

    processed_keys = load_processed_keys()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        record("DISCOVERY_STARTED", url=job_url)

        # ── DESTINATION RESOLUTION ────────────────────────────────────────────
        try:
            dest = await ApplyDestinationResolver.resolve_destination(page, job_url)
        except Exception as e:
            result["failure_kind"] = "APPLICATION_DESTINATION_FAILURE"
            result["failure_reason"] = str(e)
            result["final_status"] = "APPLICATION_BLOCKED"
            result["dom_snapshots"]["destination_failure"] = await dom_forensics(page, company, "dest_fail", run_dir)
            await browser.close()
            return result

        if dest.is_network_failure:
            result["failure_kind"] = "NETWORK_FAILURE"
            result["failure_reason"] = dest.error_reason
            result["final_status"] = "APPLICATION_BLOCKED"
            result["dom_snapshots"]["network_failure"] = await dom_forensics(page, company, "network_fail", run_dir)
            await browser.close()
            return result

        if dest.is_maintenance:
            result["failure_kind"] = "APPLICATION_DESTINATION_FAILURE"
            result["failure_reason"] = dest.error_reason
            result["final_status"] = "APPLICATION_BLOCKED"
            result["dom_snapshots"]["maintenance"] = await dom_forensics(page, company, "maintenance", run_dir)
            await browser.close()
            return result

        record("JOB_DETAIL_REACHED", url=dest.final_url)
        if dest.apply_control_found:
            record("APPLY_CONTROL_FOUND", selector=dest.apply_control_selector)
        record("APPLICATION_DESTINATION_RESOLVED", url=dest.final_url, redirect_chain=dest.redirect_chain)

        final_url = dest.final_url
        canon_key = get_canonical_requisition_key(final_url)
        result["canonical_key"] = canon_key
        sp(f"  [{company}] Canonical Key: {canon_key}")

        if canon_key in processed_keys:
            result["failure_kind"] = "DUPLICATE_APPLICATION"
            result["failure_reason"] = "Canonical key already in applied_urls_history"
            result["final_status"] = "DUPLICATE_APPLICATION"
            await browser.close()
            return result

        # ── PORTAL DETECTION ─────────────────────────────────────────────────
        try:
            portal_id = await PortalDetector.detect(page)
            result["ats_detected"] = portal_id.type.upper()
            record("PORTAL_VERIFIED", portal_type=portal_id.type.upper(), confidence=portal_id.confidence)
        except Exception as e:
            result["ats_detected"] = "UNKNOWN"

        # ── CAPTCHA EARLY CHECK ───────────────────────────────────────────────
        snap = await dom_forensics(page, company, "post_destination", run_dir)
        result["dom_snapshots"]["post_destination"] = snap
        if snap.get("captcha_detected"):
            record("CAPTCHA_DETECTED", captcha_type=snap.get("captcha_type"),
                   captcha_iframe=snap.get("captcha_iframe_url"))
            result["failure_kind"] = "CAPTCHA"
            result["failure_reason"] = f"{snap.get('captcha_type')} captcha detected: {snap.get('captcha_iframe_url')}"
            result["final_status"] = "HUMAN_ACTION_REQUIRED_CAPTCHA"
            await browser.close()
            return result

        # ── RESUME UPLOAD ─────────────────────────────────────────────────────
        resume_path = os.path.join(base_dir, f"Vinay_Khosya_{company}_diag_Resume.pdf")
        generate_valid_pdf(resume_path)

        resume_uploaded = False
        try:
            file_input = await page.query_selector("input[type='file']")
            if file_input:
                record("RESUME_UPLOAD_STARTED", filename=os.path.basename(resume_path),
                       file_size=os.path.getsize(resume_path))
                await file_input.set_input_files(resume_path)
                await page.wait_for_timeout(3000)
                resume_uploaded = True
                record("RESUME_UPLOADED", filename=os.path.basename(resume_path))

                # Wait for async processing
                for _ in range(10):
                    body = (await page.inner_text("body")).lower()
                    if any(w in body for w in ["analyzing", "uploading...", "processing...", "parsing"]):
                        record("RESUME_PROCESSING")
                        await page.wait_for_timeout(3000)
                    else:
                        break
                record("RESUME_PROCESSING_COMPLETE")
            else:
                result["failure_kind"] = "RESUME_UPLOAD_FAILURE"
                result["failure_reason"] = "No file input found on page"
        except Exception as e:
            result["failure_kind"] = "RESUME_UPLOAD_FAILURE"
            result["failure_reason"] = str(e)

        # ── FORM FIELD DETECTION ──────────────────────────────────────────────
        required_total = 0
        required_filled = 0
        unresolved_fields = []
        try:
            required_inputs = await page.query_selector_all(
                "input[required], input[aria-required='true'], textarea[required], select[required]"
            )
            required_total = len(required_inputs)

            profile = DEFAULT_CANDIDATE_PROFILE
            field_map = {
                "name": profile.get("name", "Vinay Khosya"),
                "email": profile.get("email", "vinay.khosya.ug23@nsut.ac.in"),
                "phone": profile.get("phone", "+919996303072"),
                "first_name": "Vinay",
                "last_name": "Khosya",
                "linkedin": profile.get("linkedin", "https://linkedin.com/in/vinaykhosya"),
                "github": profile.get("github", "https://github.com/vinaykhosya"),
            }

            for inp in required_inputs:
                try:
                    inp_name = (await inp.get_attribute("name") or "").lower()
                    inp_id = (await inp.get_attribute("id") or "").lower()
                    placeholder = (await inp.get_attribute("placeholder") or "").lower()
                    inp_type = (await inp.get_attribute("type") or "text").lower()
                    filled = False

                    for key, val in field_map.items():
                        if key in inp_name or key in inp_id or key in placeholder:
                            try:
                                await inp.fill(val)
                                required_filled += 1
                                filled = True
                            except Exception:
                                pass
                            break

                    if not filled:
                        lbl = await page.query_selector(f"label[for='{await inp.get_attribute('id')}']")
                        lbl_text = (await lbl.inner_text()).strip() if lbl else ""
                        unresolved_fields.append({
                            "label": lbl_text,
                            "name": inp_name, "id": inp_id,
                            "field_type": inp_type,
                            "reason_unresolved": "No matching profile key"
                        })
                except Exception:
                    pass

            if required_total > 0:
                record("REQUIRED_FIELDS_DETECTED", total=required_total)
            if required_filled > 0:
                record("REQUIRED_FIELDS_FILLED", filled=required_filled, total=required_total)
        except Exception as e:
            pass

        result["required_fields_total"] = required_total
        result["required_fields_filled"] = required_filled
        result["required_fields_unresolved"] = unresolved_fields
        record("FORM_FIELDS_SUMMARY", required_total=required_total,
               required_filled=required_filled,
               unresolved=len(unresolved_fields))

        # ── REVIEW PAGE CHECK ─────────────────────────────────────────────────
        body_text = (await page.inner_text("body")).lower()
        review_reached = ("review" in body_text or "review your" in body_text or
                          "confirm" in body_text)
        if review_reached:
            record("REVIEW_PAGE_REACHED", url=page.url)

        # ── SUBMIT CONTROL SCAN ───────────────────────────────────────────────
        record("SUBMIT_CONTROL_SEARCH_STARTED")
        snap_review = await dom_forensics(page, company, "review_page", run_dir)
        result["dom_snapshots"]["review_page"] = snap_review

        scan_result = await SubmitControlDetector.scan_page(page)
        result["submit_scan"] = {
            "found": scan_result.found,
            "candidates_count": len(scan_result.candidates),
            "diagnostic_reason": scan_result.diagnostic_reason,
            "best_candidate": scan_result.best_candidate.__dict__ if scan_result.best_candidate else None
        }

        if scan_result.found and scan_result.best_candidate:
            bc = scan_result.best_candidate
            record("SUBMIT_CONTROL_FOUND", text=bc.text, confidence=bc.confidence,
                   enabled=bc.enabled, visible=bc.visible)
            if bc.enabled:
                record("SUBMIT_CONTROL_ENABLED")
                record("SUBMIT_ELIGIBILITY_REACHED")
                # NOTE: NOT clicking submit — diagnostic only
                result["failure_kind"] = "NONE"
                result["failure_reason"] = "Diagnostic run: submit eligible but click not authorized in diagnostic mode"
                result["final_status"] = "SUBMIT_ELIGIBLE_NOT_CLICKED"
            else:
                result["failure_kind"] = "SUBMIT_DISABLED"
                result["failure_reason"] = f"Submit control '{bc.text}' found but disabled"
                result["final_status"] = "APPLICATION_BLOCKED"
        else:
            record("SUBMIT_CONTROL_NOT_FOUND",
                   diagnostic=scan_result.diagnostic_reason,
                   candidates=len(scan_result.candidates))
            # Determine the most specific failure kind
            if snap_review.get("captcha_detected"):
                result["failure_kind"] = "CAPTCHA"
            elif scan_result.diagnostic_reason == "MANDATORY_LOGIN_REQUIRED":
                result["failure_kind"] = "AUTHENTICATION_FAILURE"
            elif scan_result.diagnostic_reason == "RESUME_PROCESSING_INCOMPLETE":
                result["failure_kind"] = "RESUME_PROCESSING_FAILURE"
            elif scan_result.diagnostic_reason == "REQUIRED_FIELDS_VALIDATION_ERROR_PRESENT":
                result["failure_kind"] = "FIELD_MAPPING_FAILURE"
            elif scan_result.diagnostic_reason == "APPLICATION_IN_WIZARD_STEP_NOT_FINAL_REVIEW":
                result["failure_kind"] = "REVIEW_DETECTION_FAILURE"
            else:
                result["failure_kind"] = "SUBMIT_DETECTION_FAILURE"
            result["failure_reason"] = scan_result.diagnostic_reason or "Submit control not found in DOM"
            result["final_status"] = "APPLICATION_BLOCKED"

        await browser.close()
    return result


async def run_root_cause_diagnostic():
    run_id = f"rcd_{time.strftime('%Y%m%d_%H%M%S')}"
    timestamp_str = time.strftime("%Y%m%d_%H%M%S")

    diag_root = os.path.join(base_dir, "data", "diagnostics", "root_cause")
    run_dir = os.path.join(diag_root, run_id)
    os.makedirs(run_dir, exist_ok=True)

    sp("=" * 80)
    sp(f"HELIOS V5.0 — FINAL ROOT-CAUSE DIAGNOSTIC RUNNER [{run_id}]")
    sp("=" * 80)

    results = []
    for target in DIAGNOSTIC_TARGETS:
        try:
            r = await run_single_diagnostic(target, run_dir)
            results.append(r)
        except Exception as e:
            sp(f"[FATAL] {target['company']}: {e}")
            results.append({
                "company": target["company"],
                "job_url": target["job_url"],
                "ats_expected": target["ats_expected"],
                "ats_detected": "UNKNOWN",
                "canonical_key": None,
                "milestones": {},
                "failure_kind": "BROWSER_FAILURE",
                "failure_reason": str(e),
                "final_status": "APPLICATION_BLOCKED",
                "dom_snapshots": {}
            })

    # ── MILESTONE COUNTS ──────────────────────────────────────────────────────
    total = len(results)
    milestone_keys = [
        "DISCOVERY_STARTED", "JOB_DETAIL_REACHED", "APPLICATION_DESTINATION_RESOLVED",
        "PORTAL_VERIFIED", "RESUME_UPLOADED", "RESUME_PROCESSING_COMPLETE",
        "REQUIRED_FIELDS_FILLED", "REVIEW_PAGE_REACHED",
        "SUBMIT_CONTROL_FOUND", "SUBMIT_CONTROL_ENABLED",
        "SUBMIT_ELIGIBILITY_REACHED"
    ]
    milestone_counts = {k: sum(1 for r in results if k in r.get("milestones", {})) for k in milestone_keys}
    milestone_counts["confirmed"] = 0

    failure_dist: Dict[str, int] = {k: 0 for k in FAILURE_KINDS}
    for r in results:
        fk = r.get("failure_kind", "NONE")
        if fk in failure_dist:
            failure_dist[fk] += 1

    portal_results = {r["company"]: {
        "ats_expected": r["ats_expected"],
        "ats_detected": r["ats_detected"],
        "final_status": r["final_status"],
        "failure_kind": r["failure_kind"],
        "milestones_reached": list(r.get("milestones", {}).keys())
    } for r in results}

    # ── ROOT CAUSE VERDICT ────────────────────────────────────────────────────
    before_form = sum(1 for r in results if "APPLICATION_FORM_REACHED" not in r.get("milestones", {}))
    after_form = sum(1 for r in results if "APPLICATION_FORM_REACHED" in r.get("milestones", {}))
    reached_review = milestone_counts["REVIEW_PAGE_REACHED"]
    submit_found = milestone_counts["SUBMIT_CONTROL_FOUND"]
    submit_enabled = milestone_counts["SUBMIT_CONTROL_ENABLED"]
    eligible = milestone_counts["SUBMIT_ELIGIBILITY_REACHED"]
    confirmed = 0

    captcha_count = failure_dist.get("CAPTCHA", 0) + failure_dist.get("HUMAN_ACTION_REQUIRED_CAPTCHA", 0)
    network_count = failure_dist.get("NETWORK_FAILURE", 0) + failure_dist.get("DNS_FAILURE", 0) + failure_dist.get("BROWSER_FAILURE", 0)
    submit_detect_fail = failure_dist.get("SUBMIT_DETECTION_FAILURE", 0)

    primary_root_cause = ""
    secondary_root_causes = []
    not_root_causes = []
    recommended_fixes = []

    if submit_detect_fail > 0 and submit_detect_fail >= total // 2:
        primary_root_cause = (
            "Final submission controls are not correctly detected on company-specific "
            "application UIs. SubmitControlDetector.scan_page fails to identify the "
            "actual submit button because company portals use non-standard markup "
            "(modal flows, JS-rendered buttons, role-less elements)."
        )
        recommended_fixes.append("Extend SubmitControlDetector with deeper DOM traversal and modal-flow step tracking (Apply Now → modal → Continue → Submit).")

    if captcha_count > 0:
        secondary_root_causes.append(f"CAPTCHA blocking: {captcha_count}/{total} jobs blocked by invisible or visible CAPTCHA challenges.")
        recommended_fixes.append("Detect CAPTCHA early and classify as HUMAN_ACTION_REQUIRED_CAPTCHA without attempting submission.")

    if network_count > 0:
        secondary_root_causes.append(f"Network/Browser navigation failure: {network_count}/{total} jobs could not be reached.")
        recommended_fixes.append("Add DNS/HTTP fallback and retry with fresh browser context for chrome-error:// failures.")

    if milestone_counts["RESUME_UPLOADED"] > 0:
        not_root_causes.append(
            "Resume upload is not the primary problem: "
            f"{milestone_counts['RESUME_UPLOADED']}/{total} reachable applications completed resume upload."
        )

    report = {
        "run_id": run_id,
        "timestamp": ts(),
        "total_jobs": total,
        "milestones": milestone_counts,
        "failure_distribution": failure_dist,
        "portal_results": portal_results,
        "raw_results": results,
        "root_cause_verdict": {
            "pct_blocked_before_form": round(before_form / total * 100, 1),
            "pct_reached_review": round(reached_review / total * 100, 1),
            "pct_submit_control_found": round(submit_found / total * 100, 1),
            "pct_submit_enabled": round(submit_enabled / total * 100, 1),
            "pct_submission_eligible": round(eligible / total * 100, 1),
            "pct_confirmed": 0.0,
            "pct_captcha_blocked": round(captcha_count / total * 100, 1),
            "pct_network_blocked": round(network_count / total * 100, 1),
            "PRIMARY_ROOT_CAUSE": primary_root_cause,
            "SECONDARY_ROOT_CAUSES": secondary_root_causes,
            "NOT_A_ROOT_CAUSE": not_root_causes,
            "RECOMMENDED_FIXES": recommended_fixes
        }
    }

    report_path = os.path.join(diag_root, f"root_cause_report_{timestamp_str}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    sp(f"\n[ROOT CAUSE REPORT] {report_path}")

    # ── PRINT MATRIX ──────────────────────────────────────────────────────────
    sp("\n" + "=" * 100)
    sp("PER-COMPANY MILESTONE TABLE")
    sp("=" * 100)
    hdr = f"{'Company':<18} | {'ATS Det':<10} | {'DestRes':<7} | {'Form':<5} | {'Resum':<5} | {'Flds':<5} | {'Review':<6} | {'SubFnd':<6} | {'SubEn':<5} | {'Status'}"
    sp(hdr)
    sp("-" * 100)
    for r in results:
        ms = r.get("milestones", {})
        row = (f"{r['company']:<18} | {r['ats_detected']:<10} | "
               f"{'Y' if 'APPLICATION_DESTINATION_RESOLVED' in ms else 'N':<7} | "
               f"{'Y' if 'APPLICATION_FORM_REACHED' in ms or 'RESUME_UPLOADED' in ms else 'N':<5} | "
               f"{'Y' if 'RESUME_UPLOADED' in ms else 'N':<5} | "
               f"{'Y' if 'REQUIRED_FIELDS_FILLED' in ms else 'N':<5} | "
               f"{'Y' if 'REVIEW_PAGE_REACHED' in ms else 'N':<6} | "
               f"{'Y' if 'SUBMIT_CONTROL_FOUND' in ms else 'N':<6} | "
               f"{'Y' if 'SUBMIT_CONTROL_ENABLED' in ms else 'N':<5} | "
               f"{r['final_status']}")
        sp(row)
    sp("=" * 100)

    sp("\n" + "=" * 80)
    sp("ROOT CAUSE VERDICT")
    sp("=" * 80)
    v = report["root_cause_verdict"]
    sp(f"  Blocked before form:        {v['pct_blocked_before_form']}%")
    sp(f"  Reached review page:        {v['pct_reached_review']}%")
    sp(f"  Submit control found:       {v['pct_submit_control_found']}%")
    sp(f"  Submit control enabled:     {v['pct_submit_enabled']}%")
    sp(f"  Submission eligible:        {v['pct_submission_eligible']}%")
    sp(f"  Confirmed submissions:      {v['pct_confirmed']}%")
    sp(f"  CAPTCHA blocked:            {v['pct_captcha_blocked']}%")
    sp(f"  Network blocked:            {v['pct_network_blocked']}%")
    sp("")
    sp(f"  PRIMARY ROOT CAUSE: {v['PRIMARY_ROOT_CAUSE']}")
    for s in v["SECONDARY_ROOT_CAUSES"]:
        sp(f"  SECONDARY: {s}")
    for n in v["NOT_A_ROOT_CAUSE"]:
        sp(f"  NOT ROOT CAUSE: {n}")
    sp("=" * 80)
    return report_path


if __name__ == "__main__":
    asyncio.run(run_root_cause_diagnostic())
