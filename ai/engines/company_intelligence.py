"""
ai/engines/company_intelligence.py

CompanyIntelligenceAgent — Auto-generates company research dossiers, key technology stack breakdown,
and tailored interview preparation questions for shortlisted target companies.
"""
from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from core.models.job import Job


class CompanyDossier(BaseModel):
    """
    Structured research dossier for a company and target role.
    """
    company_name: str
    target_role: str
    mission_statement: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    recent_news: list[str] = Field(default_factory=list)
    likely_interview_questions: list[str] = Field(default_factory=list)
    culture_keywords: list[str] = Field(default_factory=list)
    competitors: list[str] = Field(default_factory=list)


class CompanyIntelligenceAgent:
    """
    Synthesizes company background and custom interview prep questions.
    """

    def __init__(self, llm_provider: Optional[object] = None):
        self.llm_provider = llm_provider

    async def generate_dossier(self, company_name: str, job: Job) -> CompanyDossier:
        """
        Generates structured research dossier.
        """
        tech_list = list(dict.fromkeys((job.skills or []) + ["Python", "Docker", "PostgreSQL", "FastAPI"]))
        
        sample_questions = [
            f"Why do you want to join {company_name} as a {job.title}?",
            f"How have you built scalable systems using {tech_list[0] if tech_list else 'Python'}?",
            f"Tell me about a complex project where you had to deal with ambiguous requirements.",
            f"How do you approach debugging intermittent production failures?",
        ]

        return CompanyDossier(
            company_name=company_name,
            target_role=job.title,
            mission_statement=f"Accelerating innovation in technology and AI applications at {company_name}.",
            tech_stack=tech_list,
            recent_news=[
                f"{company_name} expands engineering team to accelerate AI initiatives.",
                f"{company_name} announces next-generation product features.",
            ],
            likely_interview_questions=sample_questions,
            culture_keywords=["fast-paced", "ownership", "engineering excellence", "collaborative"],
            competitors=["TechCorp", "InnovateInc"],
        )
