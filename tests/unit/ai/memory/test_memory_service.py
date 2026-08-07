"""
tests/unit/ai/memory/test_memory_service.py

Unit tests for MemoryService caching, Q&A storage, and duplicate application tracking.
"""
import pytest
from unittest.mock import AsyncMock
from ai.memory.service import MemoryService


@pytest.mark.asyncio
async def test_memory_service_questionnaire_qa():
    memory = MemoryService()
    question = "Are you legally authorized to work in India?"
    answer = "Yes"

    # Initially empty
    assert await memory.get_standard_answer(question) is None

    # Store and retrieve
    await memory.store_standard_answer(question, answer)
    assert await memory.get_standard_answer(question) == "Yes"

    # Case-insensitive retrieval test
    alt_question = "ARE YOU LEGALLY AUTHORIZED TO WORK IN INDIA?"
    assert await memory.get_standard_answer(alt_question) == "Yes"


@pytest.mark.asyncio
async def test_memory_service_has_applied():
    mock_app_repo = AsyncMock()
    mock_app_repo.get_by_user_and_job.return_value = None

    memory = MemoryService(application_repo=mock_app_repo)

    # Initial check (not applied)
    assert await memory.has_applied(job_id="job_123", user_id="user_456") is False

    # Record application
    await memory.record_application(job_id="job_123", user_id="user_456")

    # Fast in-memory hit
    assert await memory.has_applied(job_id="job_123", user_id="user_456") is True
