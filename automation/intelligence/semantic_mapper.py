"""
automation/intelligence/semantic_mapper.py

Helios v5.0 Semantic Mapper.
The central bridge between PageSchema and ExecutionPlan contracts.
Maps each detected element to a SemanticValue with an explicit value_source, confidence score,
requires_llm flag, and recovery_required indicator.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from automation.intelligence.contracts import PageSchema, DetectedElement, ElementSemantic
from automation.fillers.semantic_filler import DEFAULT_CANDIDATE_PROFILE


class ValueSource(Enum):
    CANDIDATE_PROFILE = "CANDIDATE_PROFILE"
    VERIFIED_MEMORY = "VERIFIED_MEMORY"
    DETERMINISTIC_RULE = "DETERMINISTIC_RULE"
    GROQ_LLM = "GROQ_LLM"
    NONE = "NONE"


@dataclass
class SemanticValue:
    element_id: str
    semantic: ElementSemantic
    value: Optional[str]
    value_source: ValueSource
    confidence: float
    requires_llm: bool
    recovery_required: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticMapping:
    page_type: str
    mapped_values: List[SemanticValue] = field(default_factory=list)
    unresolved_count: int = 0
    overall_confidence: float = 1.0
    requires_human_recovery: bool = False


class SemanticMapper:
    def __init__(self, candidate_profile: Optional[Dict[str, Any]] = None, verified_memory: Optional[Dict[str, str]] = None):
        self.profile = candidate_profile or DEFAULT_CANDIDATE_PROFILE
        self.memory = verified_memory or {}

    def map_schema(self, schema: PageSchema) -> SemanticMapping:
        """
        Maps PageSchema elements to SemanticValue contracts.
        Only unresolved REQUIRED fields trigger human_recovery_needed.
        """
        mapped: List[SemanticValue] = []
        unresolved = 0
        confidences: List[float] = []
        human_recovery_needed = False

        for elem in schema.fields:
            sem = elem.semantic
            val = None
            source = ValueSource.NONE
            conf = elem.confidence
            req_llm = False
            rec_req = False

            # Check 1: CandidateProfile Factual Lookup
            if sem == ElementSemantic.FIRST_NAME or sem == ElementSemantic.FULL_NAME:
                val = self.profile.get("name", "Vinay Khosya")
                source = ValueSource.CANDIDATE_PROFILE
                conf = min(conf, 0.99)
            elif sem == ElementSemantic.LAST_NAME:
                val = self.profile.get("last_name", "Khosya")
                source = ValueSource.CANDIDATE_PROFILE
                conf = min(conf, 0.99)
            elif sem == ElementSemantic.EMAIL:
                val = self.profile.get("email", "vinay.khosya.ug23@nsut.ac.in")
                source = ValueSource.CANDIDATE_PROFILE
                conf = min(conf, 0.99)
            elif sem == ElementSemantic.PHONE:
                val = self.profile.get("phone", "+919996303072")
                source = ValueSource.CANDIDATE_PROFILE
                conf = min(conf, 0.99)
            elif sem == ElementSemantic.ORGANIZATION:
                val = self.profile.get("org", "NSUT Delhi")
                source = ValueSource.CANDIDATE_PROFILE
                conf = min(conf, 0.99)
            elif sem == ElementSemantic.LINKEDIN:
                val = self.profile.get("linkedin", "https://linkedin.com/in/vinaykhosya")
                source = ValueSource.CANDIDATE_PROFILE
                conf = min(conf, 0.99)
            elif sem == ElementSemantic.GITHUB:
                val = self.profile.get("github", "https://github.com/vinaykhosya")
                source = ValueSource.CANDIDATE_PROFILE
                conf = min(conf, 0.99)

            # Check 2: Verified Q&A Memory Lookup
            elif elem.element_id in self.memory:
                val = self.memory[elem.element_id]
                source = ValueSource.VERIFIED_MEMORY
                conf = 1.0

            # Check 3: Unresolved Unknown Field
            else:
                val = None
                source = ValueSource.NONE
                conf = 0.30
                req_llm = True
                rec_req = True
                if elem.metadata.get("is_required", False):
                    unresolved += 1
                    human_recovery_needed = True

            confidences.append(conf)
            mapped.append(
                SemanticValue(
                    element_id=elem.element_id,
                    semantic=sem,
                    value=val,
                    value_source=source,
                    confidence=conf,
                    requires_llm=req_llm,
                    recovery_required=rec_req
                )
            )

        overall_conf = min(confidences) if confidences else 1.0

        return SemanticMapping(
            page_type=schema.page_type.value,
            mapped_values=mapped,
            unresolved_count=unresolved,
            overall_confidence=overall_conf,
            requires_human_recovery=human_recovery_needed or schema.has_captcha or schema.has_login_prompt
        )
