"""
tests/test_semantic_filler.py

Unit tests for SemanticFormEngine and Q&A Decision Hierarchy.
"""
import pytest
from automation.fillers.semantic_filler import SemanticFormEngine


def test_semantic_filler_memory_match():
    engine = SemanticFormEngine()
    ans, source, conf = engine.resolve_question("Are you legally authorized to work in India?")
    assert ans == "Yes"
    assert source == "MEMORY"
    assert conf == 1.0


def test_semantic_filler_profile_derivation():
    engine = SemanticFormEngine()
    ans, source, conf = engine.resolve_question("Do you now or in the future require visa sponsorship?")
    assert ans == "No"
    assert source == "CANDIDATE_PROFILE"
    assert conf >= 0.95


def test_semantic_filler_unknown_recovery_required():
    engine = SemanticFormEngine()
    ans, source, conf = engine.resolve_question("What is your current security clearance level?")
    assert ans is None
    assert source == "RECOVERY_REQUIRED"
    assert conf == 0.0
