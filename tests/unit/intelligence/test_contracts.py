"""
tests/unit/intelligence/test_contracts.py

Unit tests for Helios v5.0 Data Contracts.
Verifies contracts, confidence bounds, serialization, and EvidencePayload integrity rules.
"""
import pytest
from automation.intelligence.contracts import (
    ElementSemantic,
    ActionType,
    PageType,
    RecoveryReason,
    DetectedElement,
    PageSchema,
    PlannedAction,
    ExecutionPlan,
    ActionExecution,
    EvidencePayload
)


def test_detected_element_confidence_bounds():
    # Valid element
    elem = DetectedElement(
        element_id="input-email",
        selector_used="input[type='email']",
        tag_name="input",
        element_type="text",
        semantic=ElementSemantic.EMAIL,
        confidence=0.95
    )
    assert elem.confidence == 0.95

    # Out of bounds confidence should raise ValueError
    with pytest.raises(ValueError):
        DetectedElement(
            element_id="bad",
            selector_used="css",
            tag_name="input",
            element_type="text",
            semantic=ElementSemantic.UNKNOWN,
            confidence=1.5
        )


def test_execution_plan_serialization():
    action = PlannedAction(
        action_id="act-1",
        action_type=ActionType.FILL,
        target_semantic=ElementSemantic.FIRST_NAME,
        target_selector="#first_name",
        value_to_fill="Vinay Khosya",
        confidence=0.99
    )
    plan = ExecutionPlan(
        page_type=PageType.APPLICATION_FORM,
        actions=[action],
        submission_allowed=True,
        recovery_required=False,
        recovery_reason=RecoveryReason.NONE,
        min_action_confidence=0.99
    )

    plan_dict = plan.to_dict()
    assert plan_dict["page_type"] == "APPLICATION_FORM"
    assert plan_dict["actions_count"] == 1
    assert plan_dict["submission_allowed"] is True
    assert plan_dict["recovery_reason"] == "NONE"


def test_evidence_payload_golden_rule():
    # Case 1: submit_clicked is False -> MUST return False for strong evidence
    evidence1 = EvidencePayload(
        submit_clicked=False,
        live_dom_confirmation=True,
        application_id="REQ-TEST",
        application_id_source="LIVE_PORTAL_DOM"
    )
    assert evidence1.is_strong_evidence() is False

    # Case 2: Synthetic/Test ID source -> MUST return False if no live DOM confirmation
    evidence2 = EvidencePayload(
        submit_clicked=True,
        live_dom_confirmation=False,
        application_id="MOCK-ID-123",
        application_id_source="TEST_MOCK"
    )
    assert evidence2.is_strong_evidence() is False

    # Case 3: submit_clicked is True AND live DOM confirmation is True -> STRONG evidence!
    evidence3 = EvidencePayload(
        submit_clicked=True,
        live_dom_confirmation=True,
        application_id="REQ-LIVE-9948",
        application_id_source="LIVE_PORTAL_DOM",
        url_before="https://jobs.lever.co/cred/123/apply",
        url_after="https://jobs.lever.co/cred/123/thanks"
    )
    assert evidence3.is_strong_evidence() is True


def test_action_execution_forensic_tracking():
    exec_record = ActionExecution(
        action_id="act-101",
        action_type=ActionType.FILL,
        target_semantic=ElementSemantic.EMAIL,
        target_selector="input[name='email']",
        attempted=True,
        succeeded=True
    )
    assert exec_record.action_id == "act-101"
    assert exec_record.succeeded is True
    assert exec_record.error is None
    assert exec_record.timestamp != ""
