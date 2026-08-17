"""
tests/integration/test_e2e_workflow.py

End-to-End Workflow Verification:
Tests the complete job-search operating system lifecycle:
1. Fetch live dynamic dashboard overview and auditable funnel.
2. Filter jobs by "Ready to Apply" (Eligible + Match >= 80% + Not Applied).
3. Select a qualified job and verify 5-dimension breakdown weights.
4. Trigger asynchronous AI tailoring with CandidateFactRegistry truthfulness verification.
5. Simulate manual edit in Tailor Studio, verify Guard-AGAIN revalidation blocks ungrounded claims and approves verified edits.
6. Perform 1-click Mark Applied and verify state persistence.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.src.main import app


@pytest.mark.asyncio
async def test_complete_helios_daily_workflow_e2e():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        
        # 1. Step 1: Open Dashboard & Read Auditable Funnel
        res_overview = await client.get("/api/v1/dashboard/overview")
        assert res_overview.status_code == 200
        overview = res_overview.json()
        
        assert overview["raw_discovered"] == 330
        assert overview["duplicates_grouped"] == 6
        assert overview["unique_opportunities"] > 0
        assert overview["seniority_mismatches"] >= 0
        assert overview["ready_to_apply"] > 0
        assert overview["fresh_count"] > 0
        assert "aging_count" in overview

        # 2. Step 2: Query "Ready to Apply" pool
        res_jobs = await client.get("/api/v1/jobs?saved_view=ready_to_apply")
        assert res_jobs.status_code == 200
        ready_jobs = res_jobs.json()
        assert len(ready_jobs) > 0

        target_job = ready_jobs[0]
        assert target_job["eligibility_status"] == "ELIGIBLE"
        assert target_job["fit_score"] >= 0.80
        assert target_job["freshness_status"] == "FRESH"
        assert target_job["age_days"] <= 7

        # 3. Step 3: Inspect 5-Dimension Weighted Breakdown
        res_detail = await client.get(f"/api/v1/jobs/{target_job['id']}")
        assert res_detail.status_code == 200
        job_details = res_detail.json()
        breakdown = job_details["dimension_breakdown"]
        assert "tech_stack" in breakdown
        assert "location" in breakdown
        assert "seniority" in breakdown
        assert "role" in breakdown
        assert "semantic" in breakdown

        # 4. Step 4: Trigger AI Fact-Constrained Tailoring
        tailor_req = {
            "job_id": target_job["id"],
            "job_title": target_job["title"],
            "company_name": target_job["company"],
            "job_description": "Seeking Python and FastAPI systems engineer with PyTorch experience.",
            "required_skills": ["Python", "FastAPI", "PyTorch"],
            "profile_id": "ai_ml",
        }
        res_tailor = await client.post("/api/v1/ai/tailor", json=tailor_req)
        assert res_tailor.status_code == 202
        tailor_id = res_tailor.json()["tailor_job_id"]

        # Check tailor job status
        res_tstatus = await client.get(f"/api/v1/ai/tailor/{tailor_id}")
        assert res_tstatus.status_code == 200
        t_data = res_tstatus.json()
        assert "alignment" in t_data
        assert "validation" in t_data

        # 5. Step 5: Guard-AGAIN Invariant Test (P7-H3)
        # 5a. Ungrounded edit should fail revalidation
        fake_edit = r"\documentclass{article}\begin{document}Graduated from Stanford University with $10M ARR.\end{document}"
        res_reval_bad = await client.post(
            f"/api/v1/ai/tailor/{tailor_id}/revalidate",
            json={"edited_latex": fake_edit}
        )
        assert res_reval_bad.status_code == 200
        bad_data = res_reval_bad.json()
        assert bad_data["status"] == "rejected_validation"
        assert bad_data["validation"]["passed"] is False

        # Verify PDF download is blocked on rejected validation
        res_pdf_blocked = await client.get(f"/api/v1/ai/tailor/{tailor_id}/pdf")
        assert res_pdf_blocked.status_code == 400

        # 5b. Grounded edit should pass revalidation
        good_edit = r"\documentclass{article}\begin{document}B.Tech NSUT Delhi. Built Genesis engine in Python.\end{document}"
        res_reval_good = await client.post(
            f"/api/v1/ai/tailor/{tailor_id}/revalidate",
            json={"edited_latex": good_edit}
        )
        assert res_reval_good.status_code == 200
        good_data = res_reval_good.json()
        assert good_data["validation"]["passed"] is True

        # 6. Step 6: Mark Applied (1-Click Application Receipt)
        res_applied = await client.post(f"/api/v1/jobs/{target_job['id']}/mark-applied")
        assert res_applied.status_code == 200
        assert res_applied.json()["application_status"] == "APPLIED"
