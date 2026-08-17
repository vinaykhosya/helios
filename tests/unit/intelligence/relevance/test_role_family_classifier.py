"""
tests/unit/intelligence/relevance/test_role_family_classifier.py

Authoritative unit test suite for RoleFamilyClassifier, Seniority Integrity,
and Skill Match Scorer empty-state fixes in Helios v3.0.
"""
import pytest
from datetime import datetime, timezone, timedelta

from core.models.job import (
    Job,
    JobSource,
    RoleFamily,
    RoleRelevance,
    FreshnessStatus,
    FreshnessConfidence,
)
from core.models.candidate_profile import CandidateProfile
from intelligence.relevance.role_family import RoleFamilyClassifier
from intelligence.ranking.skill_match_scorer import SkillMatchScorer
from intelligence.ranking.ranker import RankingAgent
from intelligence.freshness.gate import FreshnessGate, DEFAULT_FRESHNESS_SETTINGS


@pytest.fixture
def ai_ml_profile():
    return CandidateProfile(
        id="vinay-khosya",
        profile_name="Vinay Khosya — AI & ML Systems Engineer",
        name="Vinay Khosya",
        email="vinaykhosya.contact@gmail.com",
        location="India",
        graduation_year=2024,
        target_role="AI & ML Systems Engineer",
        ideal_role_keywords=[
            "machine learning", "ml engineer", "ai engineer",
            "deep learning", "computer vision", "nlp", "llm", "ai systems"
        ],
        required_tech_stack=["Python", "PyTorch", "FastAPI", "Docker", "PostgreSQL"],
        max_experience_years=3,
        target_locations=["India", "Bengaluru", "Remote", "Delhi"],
    )


@pytest.fixture
def classifier():
    return RoleFamilyClassifier(target_profile_id="vinay-khosya")


@pytest.fixture
def gate():
    return FreshnessGate(DEFAULT_FRESHNESS_SETTINGS)


# ── 1. Production Screenshot False-Positive Regressions ───────────────────────

def test_recruiter_mongodb_classified_irrelevant(classifier, ai_ml_profile, gate):
    """
    Regression Test: Recruiter role must be classified as RECRUITING_HR, IRRELEVANT,
    and fail-closed from Ready-to-Apply regardless of freshness.
    """
    job = Job(
        source=JobSource.MANUAL,
        source_id="recruiter-01",
        source_url="https://mongodb.com/jobs/recruiter",
        title="Recruiter",
        company="MongoDB",
        location="Bengaluru, India",
        description="We are looking for a Senior Technical Recruiter to drive hiring for database engineers.",
        apply_url="https://mongodb.com/jobs/recruiter",
        posted_at=datetime.now(timezone.utc) - timedelta(days=2),
        freshness_status=FreshnessStatus.FRESH,
        freshness_confidence=FreshnessConfidence.CONFIRMED_POSTED,
        age_days=2,
        fit_score=0.88,  # Old raw fit score preserved
    )

    res = classifier.classify(job, ai_ml_profile)
    assert res.role_family == RoleFamily.RECRUITING_HR
    assert res.role_relevance == RoleRelevance.IRRELEVANT
    assert res.confidence >= 0.95

    classifier.evaluate_job(job, ai_ml_profile)
    assert job.role_relevance == RoleRelevance.IRRELEVANT
    # Hard Invariant: Irrelevant jobs NEVER enter Ready-to-Apply
    assert not gate.is_ready_to_apply(job)


def test_customer_service_classified_irrelevant(classifier, ai_ml_profile, gate):
    """
    Regression Test: Customer Service / Help Desk must be classified as CUSTOMER_SUPPORT,
    IRRELEVANT, and excluded from Ready-to-Apply.
    """
    job = Job(
        source=JobSource.MANUAL,
        source_id="cs-01",
        source_url="https://company.com/jobs/cs",
        title="Customer Service Representative",
        company="Global Corp",
        location="Remote",
        description="Handle customer inquiries, phone support, and ticket resolution in Zendesk.",
        apply_url="https://company.com/jobs/cs",
        posted_at=datetime.now(timezone.utc) - timedelta(days=1),
        freshness_status=FreshnessStatus.FRESH,
        age_days=1,
        fit_score=0.88,
    )

    res = classifier.classify(job, ai_ml_profile)
    assert res.role_family == RoleFamily.CUSTOMER_SUPPORT
    assert res.role_relevance == RoleRelevance.IRRELEVANT
    assert res.confidence >= 0.95

    classifier.evaluate_job(job, ai_ml_profile)
    assert not gate.is_ready_to_apply(job)


def test_senior_partner_solutions_architect_presales(classifier, ai_ml_profile, gate):
    """
    Regression Test: Senior Partner Solutions Architect with pre-sales JD
    must be classified as SOLUTIONS_PRE_SALES, IRRELEVANT, seniority risk, and fail Ready-to-Apply.
    """
    job = Job(
        source=JobSource.MANUAL,
        source_id="solarch-01",
        source_url="https://mongodb.com/jobs/solarch",
        title="Senior Partner Solutions Architect",
        company="MongoDB",
        location="Bengaluru, India",
        description="Deliver technical pre-sales demonstrations, manage system integrator partners, RFP responses, and CRM pipeline.",
        apply_url="https://mongodb.com/jobs/solarch",
        posted_at=datetime.now(timezone.utc) - timedelta(days=3),
        freshness_status=FreshnessStatus.FRESH,
        age_days=3,
        fit_score=0.88,
        experience_years=6,
    )

    res = classifier.classify(job, ai_ml_profile)
    assert res.role_family == RoleFamily.SOLUTIONS_PRE_SALES
    assert res.role_relevance == RoleRelevance.IRRELEVANT
    assert res.is_seniority_risk is True
    assert "senior" in res.seniority_risk_title_keywords or "architect" in res.seniority_risk_title_keywords

    classifier.evaluate_job(job, ai_ml_profile)
    assert not gate.is_ready_to_apply(job)


# ── 2. Same Title, Different JD Invariant Tests ───────────────────────────────

def test_same_title_architect_ai_systems_vs_presales(classifier, ai_ml_profile, gate):
    """
    Invariant: Title 'Solutions Architect' must NOT be unconditionally banned.
    If JD contains genuine AI/ML technical infrastructure, it is ADJACENT with high ML score.
    If JD contains pre-sales/CRM, it is IRRELEVANT.
    """
    # Positive Case: AI Solutions Architect
    ai_arch_job = Job(
        source=JobSource.MANUAL,
        source_id="ai-arch",
        source_url="https://cloud.com/jobs/ai-arch",
        title="Solutions Architect — Generative AI",
        company="Hyperscaler Cloud",
        location="Bengaluru, India",
        description="Design and build large scale LLM inference platforms using PyTorch, RAG architectures, vector databases, CUDA, and model serving.",
        apply_url="https://cloud.com/jobs/ai-arch",
        posted_at=datetime.now(timezone.utc) - timedelta(days=2),
        freshness_status=FreshnessStatus.FRESH,
        age_days=2,
        fit_score=0.92,
        experience_years=2,
    )
    res_pos = classifier.classify(ai_arch_job, ai_ml_profile)
    assert res_pos.role_family == RoleFamily.MACHINE_LEARNING_AI
    assert res_pos.role_relevance == RoleRelevance.ADJACENT
    assert res_pos.adjacent_ml_evidence_score >= 0.60
    classifier.evaluate_job(ai_arch_job, ai_ml_profile)
    assert gate.is_ready_to_apply(ai_arch_job)

    # Negative Case: Traditional Pre-Sales Solutions Architect
    presales_job = Job(
        source=JobSource.MANUAL,
        source_id="crm-arch",
        source_url="https://corp.com/jobs/crm-arch",
        title="Solutions Architect",
        company="Enterprise Software Corp",
        location="Bengaluru, India",
        description="Lead pre-sales client presentations, RFP submissions, and CRM integration consulting for enterprise deals. 5+ years required.",
        apply_url="https://corp.com/jobs/crm-arch",
        posted_at=datetime.now(timezone.utc) - timedelta(days=2),
        freshness_status=FreshnessStatus.FRESH,
        age_days=2,
        fit_score=0.85,
        experience_years=5,
    )
    res_neg = classifier.classify(presales_job, ai_ml_profile)
    assert res_neg.role_family == RoleFamily.SOLUTIONS_PRE_SALES
    assert res_neg.role_relevance == RoleRelevance.IRRELEVANT
    classifier.evaluate_job(presales_job, ai_ml_profile)
    assert not gate.is_ready_to_apply(presales_job)


def test_software_engineer_ai_platform_vs_internal_tools(classifier, ai_ml_profile, gate):
    """
    Invariant: Generic 'Software Engineer' titles require adjacent_ml_evidence_score >= 0.60
    to enter Ready-to-Apply for an AI/ML candidate.
    """
    # Case A: Software Engineer with strong ML JD
    ai_se_job = Job(
        source=JobSource.MANUAL,
        source_id="se-ai-01",
        source_url="https://stripe.com/jobs/ai-platform",
        title="Software Engineer, AI Platform",
        company="Stripe",
        location="Bengaluru, India",
        description="Build distributed training pipelines with PyTorch, FastAPI, Hugging Face, vector search, and high-throughput model serving.",
        apply_url="https://stripe.com/jobs/ai-platform",
        posted_at=datetime.now(timezone.utc) - timedelta(days=1),
        freshness_status=FreshnessStatus.FRESH,
        age_days=1,
        fit_score=0.90,
        experience_years=2,
    )
    res_ai = classifier.classify(ai_se_job, ai_ml_profile)
    assert res_ai.role_relevance == RoleRelevance.ADJACENT
    assert res_ai.adjacent_ml_evidence_score >= 0.60
    classifier.evaluate_job(ai_se_job, ai_ml_profile)
    assert gate.is_ready_to_apply(ai_se_job)

    # Case B: Software Engineer with frontend/CSS only JD
    frontend_se_job = Job(
        source=JobSource.MANUAL,
        source_id="se-fe-01",
        source_url="https://stripe.com/jobs/internal-tools",
        title="Software Engineer, Internal Tools",
        company="Stripe",
        location="Bengaluru, India",
        description="Develop internal administrative dashboards using React, CSS, HTML5, TypeScript, and TailwindCSS.",
        apply_url="https://stripe.com/jobs/internal-tools",
        posted_at=datetime.now(timezone.utc) - timedelta(days=1),
        freshness_status=FreshnessStatus.FRESH,
        age_days=1,
        fit_score=0.88,
        experience_years=2,
    )
    res_fe = classifier.classify(frontend_se_job, ai_ml_profile)
    assert res_fe.role_relevance == RoleRelevance.ADJACENT
    assert res_fe.adjacent_ml_evidence_score < 0.60
    classifier.evaluate_job(frontend_se_job, ai_ml_profile)
    # Adjacent role without ML evidence fails Ready-to-Apply gate for AI/ML profile
    assert not gate.is_ready_to_apply(frontend_se_job)


# ── 3. Core Target Roles ──────────────────────────────────────────────────────

def test_machine_learning_engineer_stripe_target(classifier, ai_ml_profile, gate):
    """
    Target AI/ML role enters Ready-to-Apply when fresh and eligible.
    """
    job = Job(
        source=JobSource.MANUAL,
        source_id="mle-stripe",
        source_url="https://stripe.com/jobs/mle",
        title="Machine Learning Engineer",
        company="Stripe",
        location="Bengaluru, India",
        description="Train and evaluate fraud detection models using PyTorch, scikit-learn, and real-time feature stores.",
        apply_url="https://stripe.com/jobs/mle",
        posted_at=datetime.now(timezone.utc) - timedelta(days=1),
        freshness_status=FreshnessStatus.FRESH,
        age_days=1,
        fit_score=0.94,
        experience_years=2,
    )

    res = classifier.classify(job, ai_ml_profile)
    assert res.role_family == RoleFamily.MACHINE_LEARNING_AI
    assert res.role_relevance == RoleRelevance.TARGET
    assert res.confidence >= 0.90

    classifier.evaluate_job(job, ai_ml_profile)
    assert gate.is_ready_to_apply(job)


# ── 4. Seniority Gate Integrity Tests ─────────────────────────────────────────

def test_senior_staff_software_engineer_seniority_mismatch(classifier, ai_ml_profile, gate):
    """
    Senior and Staff titles must be detected as Seniority Mismatches for <= 3 yr candidate profile.
    """
    job = Job(
        source=JobSource.MANUAL,
        source_id="sr-staff-01",
        source_url="https://airbnb.com/jobs/123",
        title="Senior Staff Software Engineer, Payments",
        company="Airbnb",
        location="Bengaluru, India",
        description="Lead architecture for global payments infrastructure.",
        apply_url="https://airbnb.com/jobs/123",
        posted_at=datetime.now(timezone.utc) - timedelta(days=2),
        freshness_status=FreshnessStatus.FRESH,
        age_days=2,
        fit_score=0.88,
    )

    ranker = RankingAgent(ai_ml_profile)
    sen_score = ranker._compute_seniority_score(job)
    assert sen_score <= 0.40

    rank_res = ranker.rank(job)
    assert job.eligibility_status == "SENIORITY_MISMATCH"
    assert not gate.is_ready_to_apply(job)


def test_senior_engineer_fabric_gateway_seniority_mismatch(classifier, ai_ml_profile, gate):
    """
    Regression Test: Senior Engineer must fail seniority for a 0-3 yr candidate.
    """
    job = Job(
        source=JobSource.MANUAL,
        source_id="sr-eng-01",
        source_url="https://fabric.com/jobs/456",
        title="Senior Engineer — Fabric Gateway",
        company="Fabric",
        location="Delhi, India",
        description="Lead high-performance gateway team.",
        apply_url="https://fabric.com/jobs/456",
        posted_at=datetime.now(timezone.utc) - timedelta(days=1),
        freshness_status=FreshnessStatus.FRESH,
        age_days=1,
        fit_score=0.85,
    )

    ranker = RankingAgent(ai_ml_profile)
    sen_score = ranker._compute_seniority_score(job)
    assert sen_score <= 0.40

    ranker.rank(job)
    assert job.eligibility_status == "SENIORITY_MISMATCH"
    assert not gate.is_ready_to_apply(job)


# ── 5. SkillMatchScorer Empty-State Fix ────────────────────────────────────────

def test_skill_match_scorer_empty_skills_evaluates_to_zero():
    """
    Fix verification: When a job has NO detected technical skills,
    the score must be 0.0 with has_technical_requirements=False (NEVER 1.0).
    """
    scorer = SkillMatchScorer()
    candidate_skills = ["Python", "PyTorch", "FastAPI"]
    
    # Empty job skills list (e.g. non-tech role)
    res = scorer.score(job_skills=[], candidate_skills=candidate_skills)
    assert res.overall_score == 0.0
    assert res.has_technical_requirements is False
    assert res.matched_skills == []

    # Valid job skills list
    res_valid = scorer.score(job_skills=["Python", "Docker"], candidate_skills=candidate_skills)
    assert res_valid.overall_score == 0.5
    assert res_valid.has_technical_requirements is True
    assert res_valid.matched_skills == ["Python"]
