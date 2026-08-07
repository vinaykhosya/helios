"""
intelligence/ranking/skill_extractor.py

SkillExtractor — Case-insensitive technology skill & keyword extraction.
"""
from __future__ import annotations

import re
from typing import ClassVar
from core.models.candidate_profile import CandidateProfile
from core.models.job import Job


class SkillExtractor:
    """
    Extracts tech stack skills from job postings and candidate profiles.
    """

    KNOWN_SKILLS: ClassVar[list[str]] = [
        "Python", "JavaScript", "TypeScript", "React", "Next.js", "Node.js",
        "FastAPI", "Django", "Flask", "Docker", "Kubernetes", "Podman",
        "PostgreSQL", "Redis", "MongoDB", "MySQL", "SQLite", "Elasticsearch",
        "AWS", "GCP", "Azure", "Cloudflare",
        "TensorFlow", "PyTorch", "scikit-learn", "Keras", "OpenCV",
        "LangChain", "LlamaIndex", "OpenAI API", "Anthropic", "LLM", "NLP",
        "Computer Vision", "Deep Learning", "Machine Learning", "Artificial Intelligence",
        "Git", "CI/CD", "Agile", "Scrum", "REST API", "GraphQL", "gRPC", "Kafka", "RabbitMQ",
        "C++", "Java", "Go", "Rust", "C#", ".NET", "Scala", "Kotlin", "Swift",
        "SQL", "Vector DB", "pgvector", "Pinecone", "Qdrant", "ChromaDB",
        "Linux", "Bash", "Shell", "Terraform", "Ansible"
    ]

    def extract_from_job(self, job: Job) -> list[str]:
        """
        Extracts matched skills from job title, description, and skills list.
        """
        text_parts = [job.title or "", job.description or ""]
        if job.skills:
            text_parts.extend(job.skills)

        full_text = " ".join(text_parts).lower()
        found_skills = set()

        for skill in self.KNOWN_SKILLS:
            # Word boundary regex search to prevent partial matches like 'Go' in 'Google'
            escaped_skill = re.escape(skill)
            pattern = rf"\b{escaped_skill}\b"
            if re.search(pattern, full_text, re.IGNORECASE):
                found_skills.add(skill)

        # Also preserve any explicit skills listed in job.skills
        if job.skills:
            for s in job.skills:
                found_skills.add(s)

        return sorted(list(found_skills))

    def extract_from_profile(self, profile: CandidateProfile) -> list[str]:
        """
        Extracts candidate's skills from required_tech_stack and ideal_role_keywords.
        """
        candidate_skills = set(profile.required_tech_stack)
        candidate_skills.update(profile.ideal_role_keywords)

        # Also check experience bullets for skills
        bullets_text = " ".join(profile.experience_bullets).lower()
        for skill in self.KNOWN_SKILLS:
            pattern = rf"\b{re.escape(skill)}\b"
            if re.search(pattern, bullets_text, re.IGNORECASE):
                candidate_skills.add(skill)

        return sorted(list(candidate_skills))
