"""
intelligence/relevance/role_family.py

RoleFamilyClassifier — Standalone intelligence stage for role relevance classification.
Evaluates both Job Title hypotheses and full Job Description technical evidence to categorize
opportunities into taxonomic families and candidate alignment tiers (TARGET, ADJACENT, IRRELEVANT, UNKNOWN).

Invariants:
  1. RAW MATCH SCORE != ROLE RELEVANCE != ELIGIBILITY.
  2. Clearly non-technical roles (Recruiter, Customer Support, HR, Sales) -> IRRELEVANT (Fail-closed from Ready-to-Apply).
  3. Ambiguous titles (e.g. Solutions Architect, Software Engineer) inspect full JD evidence.
     - AI Solutions Architect with PyTorch/LLM/RAG -> ADJACENT/TARGET with high ML evidence.
     - Partner Solutions Architect with CRM/Pre-sales -> IRRELEVANT / SOLUTIONS_PRE_SALES.
  4. Adjacent roles require adjacent_ml_evidence_score >= 0.60 to enter Ready-to-Apply for AI/ML profile.
  5. Architect is flagged as SENIORITY_RISK, not an instant ban, allowing junior/mid AI roles while catching 5+ yrs.
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

from core.models.job import Job, RoleFamily, RoleRelevance
from core.models.candidate_profile import CandidateProfile


class RoleRelevanceResult(BaseModel):
    """Output contract of the RoleFamilyClassifier."""
    role_family: RoleFamily
    role_relevance: RoleRelevance
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    evidence_keywords: List[str] = Field(default_factory=list)
    adjacent_ml_evidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    is_seniority_risk: bool = False
    seniority_risk_title_keywords: List[str] = Field(default_factory=list)


class RoleFamilyClassifier:
    """
    Standalone taxonomic classifier for Job Title and Job Description relevance.
    """

    # ── Non-Technical / Irrelevant Regex Patterns ──────────────────────────────
    RECRUITING_HR_PATTERNS = [
        r"\brecruiter\b", r"\brecruiting\b", r"\btalent\s+acquisition\b", r"\bhuman\s+resources\b",
        r"\bhr\s+(specialist|generalist|coordinator|partner|manager|executive|lead|associate)\b",
        r"\bsourcer\b", r"\btalent\s+partner\b", r"\brecruitment\b", r"\bpeople\s+operations\b",
        r"\bpeople\s+partner\b", r"\bheadhunter\b"
    ]

    CUSTOMER_SUPPORT_PATTERNS = [
        r"\bcustomer\s+support\b", r"\bcustomer\s+service\b", r"\bcall\s+center\b",
        r"\bhelp\s*desk\b", r"\bsupport\s+representative\b", r"\bclient\s+support\b",
        r"\bservice\s+agent\b", r"\btelecaller\b", r"\btechnical\s+support\s+(rep|agent|associate)\b"
    ]

    SALES_MARKETING_PATTERNS = [
        r"\baccount\s+executive\b", r"\bbusiness\s+development\b", r"\bbdm\b", r"\bbdr\b", r"\bsdr\b",
        r"\bsales\s+(representative|manager|specialist|lead|executive|consultant)\b",
        r"\bmarketing\s+(specialist|manager|lead|coordinator|analyst)\b",
        r"\bdigital\s+marketing\b", r"\bseo\s+specialist\b", r"\bcontent\s+writer\b",
        r"\bcopywriter\b", r"\bsocial\s+media\b", r"\bgrowth\s+marketing\b"
    ]

    OTHER_NON_TECH_PATTERNS = [
        r"\blegal\s+counsel\b", r"\bparalegal\b", r"\baccountant\b", r"\bauditor\b",
        r"\bfinancial\s+analyst\b", r"\bfinance\s+manager\b", r"\boffice\s+manager\b",
        r"\badministrative\s+assistant\b", r"\bexecutive\s+assistant\b", r"\breceptionist\b"
    ]

    SOLUTIONS_PRE_SALES_PATTERNS = [
        r"\bpartner\s+solutions\s+architect\b", r"\bpartner\s+engineer\b",
        r"\bsales\s+engineer\b", r"\bpre[\s\-]sales\b", r"\bcommercial\s+architect\b",
        r"\bclient\s+solutions\s+manager\b", r"\bdeal\s+architect\b"
    ]

    # ── Core ML / AI Patterns (Target for AI/ML lens) ──────────────────────────
    CORE_ML_AI_PATTERNS = [
        r"\bmachine\s+learning\b", r"\bml\s+engineer\b", r"\bai\s+engineer\b", r"\bapplied\s+ai\b",
        r"\bai\/ml\b", r"\bdeep\s+learning\b", r"\bcomputer\s+vision\b", r"\bnlp\s+engineer\b",
        r"\bgenerative\s+ai\b", r"\bgenai\b", r"\bllm\s+engineer\b", r"\bmlops\b",
        r"\bai\s+systems\b", r"\bresearch\s+engineer\b", r"\bdata\s+scientist\b",
        r"\bai\s+research\b", r"\bartificial\s+intelligence\b", r"\bml\s+platform\b"
    ]

    # ── Adjacent Technical Patterns ───────────────────────────────────────────
    ADJACENT_TECH_PATTERNS = [
        r"\bsoftware\s+engineer\b", r"\bsoftware\s+developer\b", r"\bbackend\b",
        r"\bback[\s\-]end\b", r"\bpython\s+engineer\b", r"\bpython\s+developer\b",
        r"\bsystems\s+engineer\b", r"\bplatform\s+engineer\b", r"\bdata\s+engineer\b",
        r"\bdistributed\s+systems\b", r"\bcloud\s+engineer\b", r"\binfrastructure\s+engineer\b",
        r"\bfull\s*stack\b", r"\bfullstack\b"
    ]

    # ── High-Precision ML / Systems Evidence Keywords (For JD Inspection) ─────
    TIER_1_ML_KEYWORDS = [
        "pytorch", "tensorflow", "keras", "hugging face", "transformers", "llm", "large language model",
        "rag", "retrieval-augmented", "vector database", "pgvector", "faiss", "qdrant", "pinecone",
        "chromadb", "cuda", "gpu", "model training", "fine-tuning", "lora", "qlora", "vllm", "triton",
        "deep learning", "neural network", "computer vision", "nlp", "reinforcement learning",
        "diffusion model", "embedding", "embeddings", "semantic search", "onnx", "tensorrt"
    ]

    TIER_2_SYSTEMS_KEYWORDS = [
        "fastapi", "python", "distributed systems", "scikit-learn", "mlops", "kubeflow", "mlflow",
        "data pipeline", "ray", "c++", "docker", "kubernetes", "model serving", "model deployment",
        "inference", "high throughput", "low latency", "redis", "kafka"
    ]

    # ── Seniority Title Keywords ──────────────────────────────────────────────
    SENIORITY_TITLE_KEYWORDS = [
        "senior", "sr.", "sr ", "staff", "principal", "lead", "architect",
        "manager", "director", "head of", "vp", "vice president", "fellow", "expert"
    ]

    def __init__(self, target_profile_id: str = "ai_ml"):
        self.target_profile_id = target_profile_id

    def classify(self, job: Job, profile: Optional[CandidateProfile] = None) -> RoleRelevanceResult:
        """
        Classifies the job opportunity into a taxonomic family and calculates its relevance
        to the active candidate profile.
        """
        title = (job.title or "").strip()
        desc = (job.description or "").strip()
        full_text = f"{title}\n{desc}".lower()
        title_lower = title.lower()

        reasons: List[str] = []
        evidence: List[str] = []
        seniority_signals: List[str] = []

        # 1. Inspect Title for Seniority Risk
        is_seniority_risk = False
        for skw in self.SENIORITY_TITLE_KEYWORDS:
            if re.search(rf"\b{re.escape(skw)}\b", title_lower):
                is_seniority_risk = True
                seniority_signals.append(skw)

        # 2. Extract ML / Technical Evidence from Full Text
        tier1_matches = []
        for kw in self.TIER_1_ML_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", full_text):
                tier1_matches.append(kw)

        tier2_matches = []
        for kw in self.TIER_2_SYSTEMS_KEYWORDS:
            if re.search(rf"\b{re.escape(kw)}\b", full_text):
                tier2_matches.append(kw)

        evidence = sorted(list(set(tier1_matches + tier2_matches)))

        # Compute Adjacent ML Evidence Score (Tier 1 = 0.25 each, Tier 2 = 0.10 each, clamped at 1.0)
        ml_score = min(1.0, (len(tier1_matches) * 0.25) + (len(tier2_matches) * 0.10))
        ml_score = round(ml_score, 2)

        # 3. Check for Explicit Non-Technical Titles
        # 3a. Recruiting / HR
        if any(re.search(p, title_lower) for p in self.RECRUITING_HR_PATTERNS):
            return RoleRelevanceResult(
                role_family=RoleFamily.RECRUITING_HR,
                role_relevance=RoleRelevance.IRRELEVANT,
                confidence=0.98,
                reasons=["Non-engineering role: Recruiting & Human Resources"],
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 3b. Customer Support
        if any(re.search(p, title_lower) for p in self.CUSTOMER_SUPPORT_PATTERNS):
            return RoleRelevanceResult(
                role_family=RoleFamily.CUSTOMER_SUPPORT,
                role_relevance=RoleRelevance.IRRELEVANT,
                confidence=0.98,
                reasons=["Non-engineering role: Customer Support & Help Desk"],
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 3c. Sales / Marketing
        if any(re.search(p, title_lower) for p in self.SALES_MARKETING_PATTERNS):
            return RoleRelevanceResult(
                role_family=RoleFamily.SALES_MARKETING,
                role_relevance=RoleRelevance.IRRELEVANT,
                confidence=0.96,
                reasons=["Non-engineering role: Sales, Marketing & Business Development"],
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 3d. Other Non-Tech
        if any(re.search(p, title_lower) for p in self.OTHER_NON_TECH_PATTERNS):
            return RoleRelevanceResult(
                role_family=RoleFamily.OTHER_NON_TECH,
                role_relevance=RoleRelevance.IRRELEVANT,
                confidence=0.98,
                reasons=["Non-engineering role: Administrative, Finance or Legal"],
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 4. Solutions Architect / Partner Engineer Handling
        is_sol_arch = any(re.search(p, title_lower) for p in self.SOLUTIONS_PRE_SALES_PATTERNS) or "solutions architect" in title_lower
        if is_sol_arch:
            # Inspect JD for genuine AI/ML technical content vs Pre-Sales
            presales_kw = ["pre-sales", "presales", "client presentations", "rfp", "crm", "deal closing", "partner management", "sales quota"]
            has_presales = any(kw in full_text for kw in presales_kw)
            has_strong_ml = len(tier1_matches) >= 2 or ml_score >= 0.50

            if has_strong_ml and not has_presales:
                # E.g. "AI Solutions Architect" with PyTorch, RAG, GPU inference
                return RoleRelevanceResult(
                    role_family=RoleFamily.MACHINE_LEARNING_AI,
                    role_relevance=RoleRelevance.ADJACENT,
                    confidence=0.85,
                    reasons=["Architect title with verified hands-on AI/ML technical infrastructure in JD"],
                    evidence_keywords=evidence,
                    adjacent_ml_evidence_score=ml_score,
                    is_seniority_risk=is_seniority_risk,
                    seniority_risk_title_keywords=seniority_signals,
                )
            else:
                # E.g. "Senior Partner Solutions Architect" with CRM / pre-sales
                return RoleRelevanceResult(
                    role_family=RoleFamily.SOLUTIONS_PRE_SALES,
                    role_relevance=RoleRelevance.IRRELEVANT,
                    confidence=0.92,
                    reasons=["Pre-sales / Partner Solutions role without core engineering focus"],
                    evidence_keywords=evidence,
                    adjacent_ml_evidence_score=ml_score,
                    is_seniority_risk=is_seniority_risk,
                    seniority_risk_title_keywords=seniority_signals,
                )

        # 5. Core ML / AI Target Roles
        if any(re.search(p, title_lower) for p in self.CORE_ML_AI_PATTERNS):
            conf = 0.95 if tier1_matches else 0.85
            return RoleRelevanceResult(
                role_family=RoleFamily.MACHINE_LEARNING_AI,
                role_relevance=RoleRelevance.TARGET,
                confidence=conf,
                reasons=["Direct title match with target AI/ML profile"],
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=max(ml_score, 0.70),
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 6. Data Engineering
        if "data engineer" in title_lower or "data platform" in title_lower or "etl" in title_lower:
            return RoleRelevanceResult(
                role_family=RoleFamily.DATA_ENGINEERING,
                role_relevance=RoleRelevance.ADJACENT,
                confidence=0.90,
                reasons=["Data Engineering role; adjacent to ML pipeline ecosystem"],
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 7. Backend & Systems Engineering
        if any(re.search(p, title_lower) for p in [r"\bbackend\b", r"\bback[\s\-]end\b", r"\bpython\b", r"\bsystems\s+engineer\b", r"\bdistributed\s+systems\b"]):
            conf = 0.90
            reasons = ["Backend/Systems engineering role; adjacent to ML serving infrastructure"]
            return RoleRelevanceResult(
                role_family=RoleFamily.BACKEND_SYSTEMS,
                role_relevance=RoleRelevance.ADJACENT,
                confidence=conf,
                reasons=reasons,
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 8. Generic Software Engineering / Full Stack
        if any(re.search(p, title_lower) for p in self.ADJACENT_TECH_PATTERNS) or "engineer" in title_lower or "developer" in title_lower:
            reasons = ["Software engineering role"]
            if ml_score >= 0.60 or len(tier1_matches) >= 2:
                reasons.append("Contains strong ML/AI technical evidence in JD")
            else:
                reasons.append("Limited ML-specific evidence in JD")

            return RoleRelevanceResult(
                role_family=RoleFamily.GENERIC_SOFTWARE,
                role_relevance=RoleRelevance.ADJACENT,
                confidence=0.85,
                reasons=reasons,
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        # 9. Fallback / Unknown Title
        if ml_score >= 0.50:
            return RoleRelevanceResult(
                role_family=RoleFamily.GENERIC_SOFTWARE,
                role_relevance=RoleRelevance.ADJACENT,
                confidence=0.70,
                reasons=["Unclassified title but contains technical ML/AI evidence in JD"],
                evidence_keywords=evidence,
                adjacent_ml_evidence_score=ml_score,
                is_seniority_risk=is_seniority_risk,
                seniority_risk_title_keywords=seniority_signals,
            )

        return RoleRelevanceResult(
            role_family=RoleFamily.OTHER_NON_TECH,
            role_relevance=RoleRelevance.UNKNOWN,
            confidence=0.50,
            reasons=["Unrecognized role title without sufficient technical evidence"],
            evidence_keywords=evidence,
            adjacent_ml_evidence_score=ml_score,
            is_seniority_risk=is_seniority_risk,
            seniority_risk_title_keywords=seniority_signals,
        )

    def evaluate_job(self, job: Job, profile: Optional[CandidateProfile] = None) -> Job:
        """
        Runs taxonomy classification on a Job and mutates its role relevance fields.
        """
        result = self.classify(job, profile)
        job.role_family = result.role_family
        job.role_relevance = result.role_relevance
        job.role_relevance_confidence = result.confidence
        job.role_relevance_reasons = result.reasons
        job.evidence_keywords = result.evidence_keywords
        job.adjacent_ml_evidence_score = result.adjacent_ml_evidence_score
        return job
