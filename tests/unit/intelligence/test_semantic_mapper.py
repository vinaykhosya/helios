"""
tests/unit/intelligence/test_semantic_mapper.py

Unit tests for SemanticMapper emitting SemanticMapping contracts.
"""
import pytest
from automation.intelligence.contracts import PageSchema, PageType, DetectedElement, ElementSemantic
from automation.intelligence.semantic_mapper import SemanticMapper, ValueSource


def test_semantic_mapper_profile_lookup():
    fields = [
        DetectedElement("f-name", "input[name='name']", "input", "text", ElementSemantic.FIRST_NAME, 0.99),
        DetectedElement("f-email", "input[name='email']", "input", "text", ElementSemantic.EMAIL, 0.99)
    ]
    schema = PageSchema(
        page_type=PageType.APPLICATION_FORM,
        ats_type="lever",
        fields=fields
    )

    mapper = SemanticMapper()
    mapping = mapper.map_schema(schema)

    assert mapping.page_type == "APPLICATION_FORM"
    assert mapping.unresolved_count == 0
    assert mapping.requires_human_recovery is False
    assert len(mapping.mapped_values) == 2

    v_name = mapping.mapped_values[0]
    assert v_name.value == "Vinay Khosya"
    assert v_name.value_source == ValueSource.CANDIDATE_PROFILE
    assert v_name.requires_llm is False


def test_semantic_mapper_unresolved_field_triggers_recovery():
    fields = [
        DetectedElement("f-unknown", "input[name='custom_q12']", "input", "text", ElementSemantic.CUSTOM_QUESTION, 0.50, metadata={"is_required": True})
    ]
    schema = PageSchema(
        page_type=PageType.APPLICATION_FORM,
        ats_type="lever",
        fields=fields
    )

    mapper = SemanticMapper()
    mapping = mapper.map_schema(schema)

    assert mapping.unresolved_count == 1
    assert mapping.requires_human_recovery is True
    assert mapping.mapped_values[0].value_source == ValueSource.NONE
    assert mapping.mapped_values[0].requires_llm is True
    assert mapping.mapped_values[0].recovery_required is True
