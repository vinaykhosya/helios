"""
tests/unit/api/test_phase7_endpoints.py

Unit tests for Phase 7 FastAPI endpoints.
Tests dynamic dashboard overview, async discovery scans, multi-profile lens switching,
and fact-constrained AI tailoring.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.src.main import app


@pytest.mark.asyncio
async def test_dashboard_overview_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/overview")
        assert response.status_code == 200
        data = response.json()
        assert "discovered" in data
        assert "strong_matches" in data
        assert "india" in data
        assert "remote" in data
        assert "seniority_mismatches" in data
        assert "active_profile_id" in data
        assert isinstance(data["discovered"], int)


@pytest.mark.asyncio
async def test_profiles_listing_and_activation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List profiles
        response = await client.get("/api/v1/profiles")
        assert response.status_code == 200
        profiles = response.json()
        assert len(profiles) >= 3
        ids = [p["id"] for p in profiles]
        assert "ai_ml" in ids
        assert "backend" in ids

        # Activate backend profile
        act_res = await client.post("/api/v1/profiles/activate", json={"profile_id": "backend"})
        assert act_res.status_code == 200
        assert act_res.json()["active_profile_id"] == "backend"

        # Switch back to ai_ml
        act_res2 = await client.post("/api/v1/profiles/activate", json={"profile_id": "ai_ml"})
        assert act_res2.status_code == 200
        assert act_res2.json()["active_profile_id"] == "ai_ml"


@pytest.mark.asyncio
async def test_async_discovery_scans_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger scan
        post_res = await client.post("/api/v1/jobs/scans?query=Software&location=India")
        assert post_res.status_code == 202
        scan_id = post_res.json()["scan_id"]
        assert scan_id.startswith("scan-")

        # Get scan status
        get_res = await client.get(f"/api/v1/jobs/scans/{scan_id}")
        assert get_res.status_code == 200
        scan_data = get_res.json()
        assert scan_data["id"] == scan_id
        assert "portals" in scan_data
        assert "ashby" in scan_data["portals"]
        assert "greenhouse" in scan_data["portals"]

        # Get latest scan
        latest_res = await client.get("/api/v1/jobs/scans/latest")
        assert latest_res.status_code == 200
        assert "discovered_count" in latest_res.json()


@pytest.mark.asyncio
async def test_jobs_filtering_and_actions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Fetch jobs
        res = await client.get("/api/v1/jobs")
        assert res.status_code == 200
        jobs = res.json()
        assert len(jobs) > 0
        
        sample_job = jobs[0]
        assert "fit_score" in sample_job
        assert "eligibility_status" in sample_job
        assert "dimension_breakdown" in sample_job

        # Test mark applied
        mark_res = await client.post(f"/api/v1/jobs/{sample_job['id']}/mark-applied")
        assert mark_res.status_code == 200
        assert mark_res.json()["application_status"] == "APPLIED"


@pytest.mark.asyncio
async def test_async_tailoring_lifecycle():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Enqueue tailoring job
        req_payload = {
            "job_id": "test-job-01",
            "job_title": "AI Systems Engineer",
            "company_name": "Razorpay",
            "job_description": "We are seeking a Python, FastAPI, and PyTorch engineer.",
            "required_skills": ["Python", "FastAPI", "PyTorch"],
            "profile_id": "ai_ml",
        }
        res = await client.post("/api/v1/ai/tailor", json=req_payload)
        assert res.status_code == 202
        tailor_id = res.json()["tailor_job_id"]
        assert tailor_id.startswith("tailor-")

        # Check tailor job status
        status_res = await client.get(f"/api/v1/ai/tailor/{tailor_id}")
        assert status_res.status_code == 200
        t_data = status_res.json()
        assert "alignment" in t_data
        assert "validation" in t_data
