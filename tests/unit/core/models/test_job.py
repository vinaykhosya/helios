"""
tests/unit/core/models/test_job.py

Unit tests for the Job Pydantic model.

These tests verify:
- Field defaults
- Enum coercion
- Salary sub-model
- model_copy() pattern for mutations
- model_dump() / model_dump_json() round-trips
"""
import pytest
from core.models.job import (
    Job, JobSource, RemotePolicy, EmploymentType,
    Salary, SalaryConfidence,
)


class TestJobDefaults:
    def test_required_fields_only(self):
        job = Job(
            source=JobSource.JOBINDEX,
            source_id="123",
            source_url="https://jobindex.dk/job/123",
            title="Engineer",
            company="Acme",
        )
        assert job.remote == RemotePolicy.ON_SITE
        assert job.employment_type == EmploymentType.FULL_TIME
        assert job.is_active is True
        assert job.skills == []
        assert job.fit_score is None
        assert job.embedding_id is None

    def test_id_is_auto_generated(self):
        job1 = Job(source=JobSource.LINKEDIN, source_id="a", source_url="u", title="T", company="C")
        job2 = Job(source=JobSource.LINKEDIN, source_id="b", source_url="u", title="T", company="C")
        assert job1.id != job2.id

    def test_enum_values_are_strings(self):
        """model_config use_enum_values=True: enum fields serialize as plain strings."""
        job = Job(source=JobSource.JOBBANK, source_id="x", source_url="u", title="T", company="C")
        dumped = job.model_dump()
        assert dumped["source"] == "jobbank"
        assert dumped["remote"] == "on_site"


class TestSalary:
    def test_salary_defaults(self):
        s = Salary()
        assert s.currency == "DKK"
        assert s.period == "annual"
        assert s.confidence == SalaryConfidence.UNKNOWN

    def test_explicit_salary(self):
        s = Salary(min=500000, max=700000, confidence=SalaryConfidence.EXPLICIT)
        assert s.min == 500000
        assert s.confidence == "explicit"  # use_enum_values


class TestJobMutation:
    def test_model_copy_for_pipeline_enrichment(self, minimal_job):
        """Pipeline stages use model_copy() — never mutate in place."""
        enriched = minimal_job.model_copy(update={"fit_score": 0.85, "city": "Copenhagen"})
        assert enriched.fit_score == 0.85
        assert enriched.city == "Copenhagen"
        assert minimal_job.fit_score is None   # original unchanged

    def test_json_round_trip(self, full_job):
        json_str = full_job.model_dump_json()
        restored = Job.model_validate_json(json_str)
        assert restored.id == full_job.id
        assert restored.skills == full_job.skills
        assert restored.salary.min == full_job.salary.min
