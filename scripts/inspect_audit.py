"""
scripts/inspect_audit.py

Inspects live jobs loaded via backend.src.api.jobs._load_master_jobs_dataset()
and performs an exhaustive adversarial audit on the live dataset.
"""
import os
import sys
import re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.src.api.jobs import _load_master_jobs_dataset
from backend.src.services.sheets_export_service import sync_local_excel_and_csv

def main():
    jobs = _load_master_jobs_dataset()
    sync_local_excel_and_csv(jobs)

    total_discovered = len(jobs)
    fresh_count = len([j for j in jobs if j.get("freshness_status") == "FRESH"])
    aging_count = len([j for j in jobs if j.get("freshness_status") == "AGING"])
    stale_count = len([j for j in jobs if j.get("freshness_status") in ["STALE", "VERY_STALE"]])
    
    target_count = len([j for j in jobs if j.get("role_relevance") == "TARGET"])
    adjacent_count = len([j for j in jobs if j.get("role_relevance") == "ADJACENT"])
    irrelevant_count = len([j for j in jobs if j.get("role_relevance") == "IRRELEVANT"])
    role_relevant_count = target_count + adjacent_count
    
    seniority_mismatch_count = len([j for j in jobs if j.get("eligibility_status") == "SENIORITY_MISMATCH"])
    eligible_count = len([j for j in jobs if j.get("eligibility_status") == "ELIGIBLE"])

    ready_to_apply = [j for j in jobs if j.get("is_ready_to_apply")]

    # 4 Critical Adversarial Zero-Checks
    non_ml_keywords = [
        "recruiter", "talent acquisition", "customer service", "customer support",
        "hr", "sales", "marketing", "account manager", "business development", "legal", "finance"
    ]
    senior_keywords = ["senior", "staff", "principal", "lead", "director", "manager", "mgr", "head of", "vp"]

    ready_but_non_ml = [
        j for j in ready_to_apply
        if j.get("role_relevance") == "IRRELEVANT"
        or (
            any(re.search(rf"\b{re.escape(k)}\b", re.sub(r'[^a-zA-Z0-9\s]', ' ', j['title'].lower())) for k in non_ml_keywords)
            and not any(re.search(rf"\b{re.escape(eng)}\b", re.sub(r'[^a-zA-Z0-9\s]', ' ', j['title'].lower())) for eng in ["engineer", "developer", "scientist", "ai", "ml"])
        )
    ]
    ready_but_senior = [
        j for j in ready_to_apply
        if j.get("eligibility_status") != "ELIGIBLE"
        or any(re.search(rf"\b{re.escape(k)}\b", re.sub(r'[^a-zA-Z0-9\s]', ' ', j['title'].lower())) for k in senior_keywords)
    ]
    ready_without_url = [
        j for j in ready_to_apply
        if not j.get("apply_url") or j.get("apply_url", "").strip() in ["", "#"]
    ]
    ready_but_stale = [
        j for j in ready_to_apply
        if j.get("freshness_status") != "FRESH" or (j.get("age_days") is not None and j.get("age_days") > 7)
    ]

    print("=" * 75)
    print("📊 HELIOS v3.0 PRODUCTION ADVERSARIAL AUDIT REPORT")
    print("=" * 75)
    print(f"Total Discovered Opportunities : {total_discovered}")
    print(f"Fresh (<=7 days)               : {fresh_count} (Aging: {aging_count}, Stale: {stale_count})")
    print(f"Role-Relevant (Target+Adjacent): {role_relevant_count} (Target ML: {target_count}, Adjacent: {adjacent_count})")
    print(f"Irrelevant Non-Tech Excluded   : {irrelevant_count}")
    print(f"Seniority Isolated (>3 yrs/Sr) : {seniority_mismatch_count} (Eligible 0-3 yrs: {eligible_count})")
    print(f"🔥 READY TO APPLY QUEUE        : {len(ready_to_apply)}")
    print("-" * 75)
    print("CRITICAL ZERO-DEFECT AUDIT CHECKS:")
    print(f"  • Ready-but-non-ML (Must be 0) : {len(ready_but_non_ml)} -> {'✅ ZERO DEFECTS (PASS)' if len(ready_but_non_ml) == 0 else '❌ DEFECT DETECTED'}")
    print(f"  • Ready-but-senior (Must be 0) : {len(ready_but_senior)} -> {'✅ ZERO DEFECTS (PASS)' if len(ready_but_senior) == 0 else '❌ DEFECT DETECTED'}")
    print(f"  • Ready-without-URL(Must be 0) : {len(ready_without_url)} -> {'✅ ZERO DEFECTS (PASS)' if len(ready_without_url) == 0 else '❌ DEFECT DETECTED'}")
    print(f"  • Ready-but-stale  (Must be 0) : {len(ready_but_stale)} -> {'✅ ZERO DEFECTS (PASS)' if len(ready_but_stale) == 0 else '❌ DEFECT DETECTED'}")
    print("=" * 75)

    print("\nALL READY-TO-APPLY QUEUED OPPORTUNITIES (ORDERED BY CONVICTION):")
    for idx, j in enumerate(ready_to_apply):
        print(f"  {idx+1:2d}. {j['title']} | {j['company']} | Rel: {j['role_relevance']} ({j['role_family']}) | Fit: {int(j['fit_score']*100)}% | Age: {j['age_days']}d | URL: {j['apply_url'][:65]}")

if __name__ == "__main__":
    main()
