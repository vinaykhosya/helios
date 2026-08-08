"""
tests/test_canonical_dedup.py

Unit tests for Canonical Application Identity (ApplicationKey) deduplication.
"""
import pytest
from automation.verifier import get_canonical_requisition_key


def test_canonical_requisition_key_lever():
    key1 = get_canonical_requisition_key("https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5")
    key2 = get_canonical_requisition_key("https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5?source=linkedin")
    key3 = get_canonical_requisition_key("https://jobs.lever.co/cred/7e4d512e-fc89-40fd-9a30-46c5459bbea5/apply?source=indeed")

    assert key1 == "lever:cred:7e4d512e-fc89-40fd-9a30-46c5459bbea5"
    assert key1 == key2 == key3


def test_canonical_requisition_key_greenhouse():
    key1 = get_canonical_requisition_key("https://boards.greenhouse.io/postman/jobs/5912345")
    key2 = get_canonical_requisition_key("https://boards.greenhouse.io/postman/jobs/5912345?gh_jid=5912345")

    assert key1 == "greenhouse:postman:5912345"
    assert key1 == key2
