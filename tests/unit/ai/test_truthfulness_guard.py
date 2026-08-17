"""
tests/unit/ai/test_truthfulness_guard.py

Unit tests for FactRegistry and TruthfulnessGuard (Invariants #11 & #12).
"""
import pytest
from ai.engines.resume.fact_registry import CandidateFactRegistry
from ai.engines.resume.truthfulness_guard import TruthfulnessGuard


def test_fact_registry_verifies_authentic_facts():
    registry = CandidateFactRegistry()
    assert registry.is_company_verified("ElectraWireless") is True
    assert registry.is_company_verified("ThirdEye AI") is True
    assert registry.is_project_verified("Genesis") is True
    assert registry.is_project_verified("CrackNonTech") is True
    assert registry.is_technology_verified("FastAPI") is True
    assert registry.is_technology_verified("PyTorch") is True
    assert registry.is_technology_verified("PostgreSQL") is True


def test_truthfulness_guard_passes_authentic_resume():
    registry = CandidateFactRegistry()
    guard = TruthfulnessGuard(registry)

    original = r"\documentclass{article}\begin{document}B.Tech at NSUT Delhi. Built Genesis in Python/FastAPI with 40% speedup.\end{document}"
    tailored = r"\documentclass{article}\begin{document}B.Tech at NSUT Delhi. Developed Genesis engine using FastAPI and PyTorch with 40% speedup.\end{document}"

    report = guard.validate(original, tailored)
    assert report.passed is True
    assert len(report.violations) == 0
    assert report.no_fabricated_degrees is True
    assert report.no_fabricated_metrics is True


def test_truthfulness_guard_rejects_fabricated_degrees():
    registry = CandidateFactRegistry()
    guard = TruthfulnessGuard(registry)

    original = r"\documentclass{article}\begin{document}B.Tech candidate at NSUT Delhi.\end{document}"
    tailored = r"\documentclass{article}\begin{document}Ph.D. in Computer Science from Stanford University.\end{document}"

    report = guard.validate(original, tailored)
    assert report.passed is False
    assert report.no_fabricated_degrees is False
    assert any("Ph.D." in v or "Stanford" in v for v in report.violations)


def test_truthfulness_guard_rejects_fabricated_metrics():
    registry = CandidateFactRegistry()
    guard = TruthfulnessGuard(registry)

    original = r"\documentclass{article}\begin{document}Built backend services in FastAPI.\end{document}"
    tailored = r"\documentclass{article}\begin{document}Scaled system generating $10M ARR across 10,000,000 users.\end{document}"

    report = guard.validate(original, tailored)
    assert report.passed is False
    assert report.no_fabricated_metrics is False
    assert any("$10M" in v or "10,000,000" in v for v in report.violations)
