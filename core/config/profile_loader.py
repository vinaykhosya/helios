"""
core/config/profile_loader.py

Loader utility for CandidateProfile domain model from YAML configuration files.
"""
from __future__ import annotations

import os
from typing import Optional
import yaml

from core.models.candidate_profile import CandidateProfile


def load_candidate_profile(config_path: Optional[str] = None) -> CandidateProfile:
    """
    Loads and parses CandidateProfile from candidate_profile.yaml.

    Args:
        config_path: Path to YAML config file. If None, defaults to config/candidate_profile.yaml.

    Returns:
        Validated CandidateProfile model instance.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If YAML is invalid or missing required profile fields.
    """
    if config_path is None:
        # Default path relative to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, "config", "candidate_profile.yaml")

    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Candidate profile config not found at: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"Invalid candidate profile YAML structure in {config_path}")

    return CandidateProfile(**data)
