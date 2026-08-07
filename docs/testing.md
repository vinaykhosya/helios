# Testing Architecture

## Overview

Helios tests are organized into three tiers matching the architecture layers.

```
tests/
├── conftest.py              # Shared fixtures (Job, Company, User stubs)
├── unit/                   # No network, no DB, no external services
│   ├── core/
│   │   ├── models/          # Job, Company, Application, User model tests
│   │   └── events/          # Event contract and correlation_id tests
│   ├── intelligence/
│   │   └── pipeline/        # Stage contract tests; stage implementation tests (Phase 3+)
│   └── ai/
│       └── engines/         # Engine output format tests (Phase 2+)
├── integration/            # Real DB (test container), real Redis, no external HTTP
│   ├── repositories/        # CRUD + query tests against live Postgres
│   ├── connectors/          # Connector tests against recorded HTTP fixtures (vcr.py)
│   └── api/                 # FastAPI TestClient tests
├── e2e/                    # Full stack (Phase 5+)
│   └── flows/               # Ingestion → ranking → notification end-to-end
├── fixtures/               # Shared static test data (JSON, SQL seed files)
└── mocks/                  # Mock implementations of interfaces
    ├── mock_connector.py    # In-memory BaseConnector implementation
    ├── mock_provider.py     # In-memory BaseProvider (returns canned completions)
    └── mock_stage.py        # Pass-through BasePipelineStage (no-op)
```

---

## Tier 1: Unit Tests (`tests/unit/`)

**Rules:**
- No database, no network, no file I/O.
- No `pytest-asyncio` unless the function under test is `async`.
- Import only from `core/`, `ai/`, and `intelligence/`.
- Never import from `backend/` or `workers/`.

**What to test:**
- Model field defaults, validation, enum coercion.
- `model_copy()` correctness (pipeline enrichment pattern).
- JSON round-trips (`model_dump_json()` → `model_validate_json()`).
- Event `event_type` derivation and `correlation_id` propagation.
- Pipeline stage order enforcement (`INGESTION_PIPELINE` list).
- Exception hierarchy (correct parent class).

**Example:**
```python
def test_job_fit_score_default():
    job = Job(source=JobSource.JOBINDEX, ...)
    assert job.fit_score is None  # set by RankerStage, not at construction

def test_correlation_id_propagation():
    parent = ConnectorRunFailed(connector="jobindex", run_id="r", error="timeout")
    child = JobDiscovered(..., correlation_id=parent.correlation_id)
    assert child.correlation_id == parent.correlation_id
```

---

## Tier 2: Integration Tests (`tests/integration/`)

**Rules:**
- Requires running Postgres and Redis (use `testcontainers` or `docker-compose -f docker-compose.test.yml`).
- HTTP calls to external portals are recorded with `pytest-recording` (VCR cassettes).
- Use a separate test database (`helios_test`) — never the development database.
- Each test that writes to the DB must run in a transaction that rolls back on teardown.

**What to test (Phase 2+):**
- Repository CRUD: create, read, update, delete for each table.
- Query correctness: filters, ordering, pagination.
- Connector normalization: given a recorded HTTP response, `normalize()` returns a valid `Job`.
- FastAPI endpoints: status codes, response schemas, error cases.

**Example:**
```python
@pytest.mark.asyncio
async def test_create_job(db_session, full_job):
    repo = JobRepository(db_session)
    stored = await repo.create(full_job)
    assert stored.id == full_job.id
    assert stored.source == "jobindex"
```

---

## Tier 3: End-to-End Tests (`tests/e2e/`)

**Phase 5+. Not yet implemented.**

**What to test:**
- Full ingestion run: connector → pipeline → DB → event → notification.
- Application flow: job URL → evaluate → resume → cover letter → PDF compile.
- Ranking accuracy: given a user profile, high-fit jobs rank above low-fit jobs.

---

## Mock Implementations (`tests/mocks/`)

### `mock_connector.py` (Phase 2)

An in-memory `BaseConnector` that returns a hardcoded list of `Job` objects. Used in unit tests for services and pipeline stages. No HTTP calls.

### `mock_provider.py` (Phase 2)

An in-memory `BaseProvider` that returns canned completion strings. Used in engine unit tests without an API key.

### `mock_stage.py` (Phase 1 available)

A pass-through `BasePipelineStage` that returns its input unchanged. Useful for testing pipeline orchestration logic without real stage implementations.

---

## Running Tests

```bash
# All unit tests (no external dependencies)
pytest tests/unit/ -v

# Integration tests (requires Postgres + Redis)
pytest tests/integration/ -v --timeout=30

# All tests with coverage
pytest tests/ --cov=core --cov=intelligence --cov=ai --cov-report=term-missing

# Single file
pytest tests/unit/core/models/test_job.py -v
```

---

## Conventions

| Convention | Rule |
|-----------|------|
| Naming | `test_<what>_<condition>.py`, `test_<what>_<condition>` |
| Fixtures | Define in `conftest.py` at the most specific scope that covers all consumers |
| Async | Use `@pytest.mark.asyncio` — never `asyncio.run()` inside tests |
| No magic numbers | Use named fixtures or constants for IDs, scores, counts |
| One assertion theme | One concept per test; multiple `assert` statements are fine if they test the same thing |
| Stage order test | `test_pipeline_order` in `test_stages.py` enforces stage sequence — update it when ADR-006 changes |
