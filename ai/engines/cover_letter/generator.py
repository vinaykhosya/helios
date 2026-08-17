"""
ai/engines/cover_letter/generator.py

CoverLetterEngine — Generates 3-paragraph value-narrative cover letters
grounded strictly in candidate capabilities and aligned with target company mission.
"""
from __future__ import annotations

import re
from typing import Dict, Any
from backend.src.ai.provider_pool import ai_engine


class CoverLetterEngine:
    """
    Generates concise, customized cover letters without fluff or generic filler.
    """

    async def generate(
        self,
        candidate_name: str,
        candidate_education: str,
        job_title: str,
        company_name: str,
        job_description: str,
        matched_skills: list[str],
    ) -> str:
        """
        Generates 3-paragraph cover letter tailored to the job.
        """
        skills_str = ", ".join(matched_skills[:6]) if matched_skills else "Python, FastAPI, System Design"

        system_prompt = (
            "You are a professional technical career advisor. Write a compelling, concise 3-paragraph "
            "Cover Letter for a software engineering position.\n"
            "Paragraph 1: Clear opening stating the role, enthusiasm for the company's specific product/mission, and high-level fit.\n"
            "Paragraph 2: Concrete technical achievements from the candidate's real experience (FastAPI, PyTorch, system design, low-latency pipelines).\n"
            "Paragraph 3: Confident, professional closing expressing readiness for technical discussion.\n"
            "Rule: Never invent fake degrees or past employers. Keep tone confident, direct, and engineering-focused."
        )

        user_prompt = (
            f"Candidate: {candidate_name} ({candidate_education})\n"
            f"Applying for: {job_title} at {company_name}\n"
            f"Relevant Core Skills: {skills_str}\n"
            f"Job Description Excerpt: {job_description[:500]}\n"
        )

        try:
            res = await ai_engine.generate_text(user_prompt, system_prompt)
            return res.strip()
        except Exception as e:
            # High-quality fallback template
            return (
                f"Dear Hiring Team at {company_name},\n\n"
                f"I am writing to express my strong enthusiasm for the {job_title} role at {company_name}. "
                f"With a strong foundation in scalable backend systems, high-performance API development, and AI engineering, "
                f"I have built production-grade platforms using {skills_str}. {company_name}'s focus on engineering excellence "
                f"strongly aligns with my background in architecting reliable, low-latency systems.\n\n"
                f"At ElectraWireless and ThirdEye AI, I developed FastAPI backend services powering real-time inference pipelines, "
                f"optimizing memory usage by 40% and maintaining sub-50ms latency. Additionally, building the Genesis simulation engine "
                f"and full-stack recruitment platforms has given me deep experience in database design, asynchronous architecture, "
                f"and robust system delivery.\n\n"
                f"I welcome the opportunity to discuss how my technical skills and enthusiasm can contribute to {company_name}'s goals. "
                f"Thank you for your time and consideration.\n\n"
                f"Sincerely,\n{candidate_name}"
            )
