"""Quick forensics dump from root_cause_report."""
import json, sys

path = "data/diagnostics/root_cause/root_cause_report_20260808_193232.json"
d = json.load(open(path))

for r in d["raw_results"]:
    company = r["company"]
    print(f"\n{'='*80}")
    print(f"COMPANY: {company}")
    print(f"ATS detected: {r.get('ats_detected')} | failure: {r.get('failure_kind')} | status: {r.get('final_status')}")

    # submit scan
    ss = r.get("submit_scan", {})
    if ss:
        print(f"Submit scan: found={ss.get('found')} | candidates={ss.get('candidates_count')} | reason={ss.get('diagnostic_reason')}")
        bc = ss.get("best_candidate") or {}
        if bc:
            print(f"  Best candidate: text={bc.get('text')!r} conf={bc.get('confidence')} "
                  f"visible={bc.get('visible')} enabled={bc.get('enabled')} "
                  f"disabled_attr={bc.get('disabled_attr')} aria_disabled={bc.get('aria_disabled')}")
            print(f"  Reasoning: {bc.get('reasoning')}")

    # snapshot data
    for snap_name, snap in r.get("dom_snapshots", {}).items():
        print(f"\n  [snapshot: {snap_name}]")
        print(f"    URL: {snap.get('url')}")
        print(f"    Title: {snap.get('page_title')}")
        print(f"    Controls: {snap.get('total_controls')}")
        print(f"    CAPTCHA: {snap.get('captcha_detected')} ({snap.get('captcha_type')})")
        print(f"    Body snippet: {snap.get('body_text_snippet','')[:500]}")
        print(f"    All controls:")
        for c in snap.get("controls", []):
            print(f"      [{c.get('tag')}/{c.get('type')}/{c.get('role')}] "
                  f"text={c.get('text')!r:40s} vis={c.get('visible')} "
                  f"dis={c.get('disabled')} aria_dis={c.get('aria_disabled')} "
                  f"bb={c.get('bounding_box')}")
        print(f"    iframes: {snap.get('iframes')}")
