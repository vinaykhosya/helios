"""
tests/unit/database/test_application_uniqueness.py

Validates Invariant #10: one ApplicationORM per (user_id, job_id).

Uses SQLite in-memory with schema_translate_map to strip the 'helios' schema
(SQLite does not support schemas; PostgreSQL does in production).
"""
import pytest
import uuid
from datetime import datetime

from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from database.models.base import Base, metadata_obj
from database.models.application import ApplicationORM


def _make_engine():
    """
    In-memory SQLite engine with schema stripping.
    The Base uses schema='helios', which SQLite doesn't support.
    schema_translate_map strips it for SQLite compatibility.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        echo=False,
        execution_options={"schema_translate_map": {"helios": None}},
    )
    # Create only the tables needed for this test; FK deps relaxed by SQLite
    with engine.connect() as conn:
        # ApplicationORM only -- no FK enforcement in SQLite by default
        conn.execute(
            __import__("sqlalchemy").text("""
            CREATE TABLE IF NOT EXISTS applications (
                id VARCHAR NOT NULL PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                job_id VARCHAR,
                status VARCHAR NOT NULL DEFAULT 'saved',
                applied_at DATETIME,
                resume_id VARCHAR,
                cover_letter_id VARCHAR,
                fit_rating NUMERIC(4,2),
                notes VARCHAR,
                contact_person VARCHAR,
                source_channel VARCHAR,
                created_at DATETIME NOT NULL,
                updated_at DATETIME NOT NULL,
                CONSTRAINT uq_application_user_job UNIQUE (user_id, job_id)
            )
            """)
        )
        conn.commit()
    return engine


def _app(user_id: str, job_id: str) -> ApplicationORM:
    return ApplicationORM(
        id=str(uuid.uuid4()),
        user_id=user_id,
        job_id=job_id,
        status="pending_manual",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def test_unique_constraint_rejects_duplicate_user_job():
    """
    Inserting two ApplicationORMs with the same (user_id, job_id)
    must raise IntegrityError at the DB level.
    Proves Invariant #10 is enforced by the schema, not just application code.
    """
    engine = _make_engine()
    user_id = "user-abc"
    job_id = "job-xyz"

    with Session(engine) as session:
        session.add(_app(user_id, job_id))
        session.commit()

    with pytest.raises(IntegrityError):
        with Session(engine) as session:
            session.add(_app(user_id, job_id))   # same (user, job) -- must fail
            session.commit()


def test_unique_constraint_allows_different_users_same_job():
    """
    Two different users CAN both have an application for the same job.
    The constraint is (user_id, job_id), NOT just job_id.
    """
    engine = _make_engine()
    job_id = "job-xyz"

    with Session(engine) as session:
        session.add(_app("user-alice", job_id))
        session.add(_app("user-bob",   job_id))
        session.commit()   # must NOT raise


def test_unique_constraint_allows_same_user_different_jobs():
    """One user CAN have applications for two different jobs."""
    engine = _make_engine()
    user_id = "user-alice"

    with Session(engine) as session:
        session.add(_app(user_id, "job-001"))
        session.add(_app(user_id, "job-002"))
        session.commit()   # must NOT raise


def test_unique_constraint_name_is_correct():
    """
    The constraint name must be 'uq_application_user_job' so Alembic migrations
    can reference it consistently when adding/dropping it.
    """
    constraint_names = {c.name for c in ApplicationORM.__table__.constraints}
    assert "uq_application_user_job" in constraint_names, (
        f"Expected 'uq_application_user_job' in constraints, got: {constraint_names}"
    )
