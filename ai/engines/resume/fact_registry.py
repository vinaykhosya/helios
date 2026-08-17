"""
ai/engines/resume/fact_registry.py

Authoritative Candidate Fact Registry.
Single source of ground truth for candidate facts, capabilities, and metrics.
Separates ground-truth facts from presentation layers (LaTeX templates).
"""
from __future__ import annotations

import re
from typing import List, Set, Dict, Any, Optional
from pydantic import BaseModel, Field


class FactCategory(BaseModel):
    name: str
    items: List[str] = Field(default_factory=list)


class CandidateFactRegistry:
    """
    Authoritative ground-truth knowledge store of verified candidate capabilities and history.
    Master LaTeX is only a presentation layer of this registry.
    """
    VERSION: str = "v1.2.0"

    def __init__(self, master_latex: str = "", profile_data: Optional[Dict[str, Any]] = None):
        self.master_latex = master_latex
        self.profile_data = profile_data or {}
        
        # Authoritative verified entities & provenance
        self.education: List[Dict[str, str]] = [
            {
                "institution": "Netaji Subhas University of Technology (NSUT Delhi)",
                "degree": "B.Tech in Artificial Intelligence and Data Science",
                "timeline": "2023 - 2027",
                "verified": True,
            }
        ]

        self.employment: List[Dict[str, str]] = [
            {
                "company": "ElectraWireless",
                "role": "AI Engineering Intern",
                "timeline": "2024",
                "verified": True,
            },
            {
                "company": "ThirdEye AI (JBM Group)",
                "role": "Software / AI Intern",
                "timeline": "2024",
                "verified": True,
            },
            {
                "company": "Gurugram Police Cyber Security Division",
                "role": "Cybersecurity / Data Analyst Intern",
                "timeline": "2023",
                "verified": True,
            }
        ]

        self.projects: List[Dict[str, str]] = [
            {
                "name": "Genesis",
                "description": "High-throughput physics & AI simulation engine built in C++ and Python",
                "verified": True,
            },
            {
                "name": "CrackNonTech",
                "description": "Full-stack prep platform for engineering students",
                "verified": True,
            },
            {
                "name": "GuardEye",
                "description": "Low-latency cybersecurity & threat scanning tool",
                "verified": True,
            }
        ]
        
        self.verified_companies: Set[str] = {
            "electrawireless",
            "thirdeye ai",
            "jbm group",
            "gurugram police",
            "cyber security division",
            "netaji subhas university of technology",
            "nsut",
        }
        
        self.verified_projects: Set[str] = {
            "genesis",
            "cracknontech",
            "guardeye",
        }
        
        self.verified_technologies: Set[str] = {
            "python", "java", "c++", "sql", "fastapi", "rest apis", "rest", "postgresql",
            "supabase", "sqlite", "redis", "pytorch", "numpy", "opencv", "onnx", "git",
            "docker", "linux", "vs code", "sqlalchemy", "pydantic", "playwright",
            "react", "typescript", "tailwind css", "html", "css", "data structures",
            "algorithms", "system design", "database design", "oop", "machine learning",
            "artificial intelligence", "deep learning", "llm", "embeddings"
        }
        
        self.verified_metrics: Set[str] = {
            "30%", "40%", "50ms", "<50ms", "100,000+", "100k+", "2 seconds", "<2s",
            "rank 4", "162,000+", "3561", "air 3561", "2023 -- 2027", "2023-2027"
        }

    def get_summary_dict(self) -> Dict[str, Any]:
        """Returns structured fact registry contents for UI audit & verification."""
        return {
            "version": self.VERSION,
            "education": self.education,
            "employment": self.employment,
            "projects": self.projects,
            "technologies_count": len(self.verified_technologies),
            "verified_metrics_count": len(self.verified_metrics),
        }

    def is_company_verified(self, company_name: str) -> bool:
        if not company_name:
            return True
        c_lower = company_name.lower().strip()
        return any(v in c_lower or c_lower in v for v in self.verified_companies)

    def is_project_verified(self, project_name: str) -> bool:
        if not project_name:
            return True
        p_lower = project_name.lower().strip()
        return any(v in p_lower or p_lower in v for v in self.verified_projects)

    def is_technology_verified(self, tech_name: str) -> bool:
        if not tech_name:
            return True
        t_lower = tech_name.lower().strip()
        return any(v in t_lower or t_lower in v for v in self.verified_technologies)


# Global singleton instance
candidate_fact_registry = CandidateFactRegistry()
