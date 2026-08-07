"""
ai/engines/base.py

BaseAIEngine re-exported from core for use within the ai/ package.

Engine catalog (Phase 1 contracts; Phase 2 implementations):

  Engine Name        | Source Material
  ─────────────────────────────────────────────────────────────────────────
  ResumeEngine       | .claude/skills/job-application-assistant/05-cv-templates.md
                     | .claude/commands/apply.md Steps 2, 4 (CV drafting)
  ─────────────────────────────────────────────────────────────────────────
  CoverLetterEngine  | .claude/skills/job-application-assistant/06-cover-letter-templates.md
                     | .claude/commands/apply.md Steps 2, 4 (cover letter drafting)
  ─────────────────────────────────────────────────────────────────────────
  ReviewerEngine     | .claude/commands/apply.md Steps 3–4 (reviewer agent)
  ─────────────────────────────────────────────────────────────────────────
  InterviewEngine    | .claude/skills/job-application-assistant/07-interview-prep.md
  ─────────────────────────────────────────────────────────────────────────
  SkillGapEngine     | .claude/skills/upskill/SKILL.md
  ─────────────────────────────────────────────────────────────────────────
  CareerAdvisorEngine| .claude/skills/job-application-assistant/04-job-evaluation.md
                     | New: holistic career advice beyond per-job evaluation
  ─────────────────────────────────────────────────────────────────────────

All engines accept a context dict and return an output dict.
Context and output schemas are documented per engine.
"""
from core.interfaces.ai_engine import BaseAIEngine

__all__ = ["BaseAIEngine"]
