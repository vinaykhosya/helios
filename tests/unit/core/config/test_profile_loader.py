"""
tests/unit/core/config/test_profile_loader.py

Unit tests for YAML CandidateProfile loader.
"""
import os
import tempfile
import pytest
from core.config.profile_loader import load_candidate_profile


def test_load_candidate_profile_default():
    profile = load_candidate_profile()
    assert profile.name == "Vinay Khosya"
    assert profile.location == "India"
    assert "Python" in profile.required_tech_stack
    assert "PHP" in profile.excluded_keywords


def test_load_candidate_profile_custom_yaml():
    yaml_content = """
    name: "Test Engineer"
    email: "test@example.com"
    location: "Remote"
    graduation_year: 2024
    years_of_experience: 1.0
    required_tech_stack: ["Go", "Kubernetes"]
    """
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".yaml") as tmp:
        tmp.write(yaml_content)
        tmp_path = tmp.name

    try:
        profile = load_candidate_profile(tmp_path)
        assert profile.name == "Test Engineer"
        assert profile.required_tech_stack == ["Go", "Kubernetes"]
        assert profile.years_of_experience == 1.0
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def test_load_candidate_profile_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_candidate_profile("/nonexistent/path/profile.yaml")
