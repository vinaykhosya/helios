"""
automation/discovery/contracts.py

Helios v5.0 Company Careers Discovery Contracts.
Defines standardized data structures for discovered requisitions.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass
class DiscoveredJob:
    title: str
    company: str
    location: str
    requisition_url: str
    canonical_key: str
    match_score: float = 0.0
    application_url: Optional[str] = None
    application_system: Optional[str] = None
    requisition_id: Optional[str] = None
    is_job_detail_page: bool = False
    tags: List[str] = field(default_factory=list)
    raw_payload: Dict[str, Any] = field(default_factory=dict)
