# Execution Order

This document defines the canonical implementation sequence for Helios.
It is a living document — update it when phases shift.

> **Rule:** Never begin a phase until the previous phase's definition of done is met.
> FastAPI should never be written before repositories exist.
> Repositories should never be written before the schema is migrated.
> The frontend should never be built before the API is stable.

---

## Phase 1 — Foundational Contracts ✅ Complete

**Deliverables:**
- Universal models (Job, Company, Application, User) — Pydantic v2
- Interfaces (BaseConnector, BasePipelineStage, BaseAIEngine, BaseProvider, BaseEventHandler)
- Event contracts (12 typed events with correlation_id)
- Domain exceptions
- Database schema (18 tables, pgvector)
- Ingestion pipeline stage contracts (6 stages, NotImplementedError)
- ConnectorRegistry
- Architecture docs, ADRs (6), pipeline doc, data schemas, testing architecture

**Validation gate:**
- [x] `python -c "import core"` — no errors, no circular imports
- [x] `python -c "import intelligence"` — no errors
- [x] `python -c "import ai"` — no errors
- [x] `core/` imports nothing from `backend/`, `ai/`, `intelligence/`
- [x] All 6 pipeline stages raise `NotImplementedError`
- [x] All 17 DB tables present in schema.sql
- [x] All events carry `event_id`, `event_type`, `occurred_at`, `correlation_id`, `metadata`

---

# Execution Order

This document defines the canonical implementation sequence for Helios.
It is a living document — update it when phases shift.

> **Rule:** Never begin a phase until the previous phase's definition of done is met.
> FastAPI should never be written before repositories exist.
> Repositories should never be written before the schema is migrated.
> The frontend should never be built before the API is stable.

---

## Phase 1 — Foundational Contracts ✅ Complete

**Deliverables:**
- Universal models (Job, Company, Application, User) — Pydantic v2
- Interfaces (BaseConnector, BasePipelineStage, BaseAIEngine, BaseProvider, BaseEventHandler, Repository Protocols)
- Event contracts (12 typed events with correlation_id and event_type)
- Domain exceptions
- Database schema (18 tables, pgvector)
- Ingestion pipeline stage contracts (6 stages, NotImplementedError)
- ConnectorRegistry
- Architecture docs, ADRs (6), pipeline doc, data schemas, testing architecture, and validation checks.

**Validation gate:**
- [x] `python -c "import core"` — no errors, no circular imports
- [x] `python -c "import intelligence"` — no errors
- [x] `python -c "import ai"` — no errors
- [x] `core/` imports nothing from `backend/`, `ai/`, `intelligence/`
- [x] All 6 pipeline stages raise `NotImplementedError`
- [x] All 17 DB tables present in schema.sql
- [x] All events carry `event_id`, `event_type`, `occurred_at`, `correlation_id`, `metadata`

---

## Phase 2 — Persistence Layer + Backend

**Objective:** Make jobs writable and readable. No AI yet. No connectors yet. No authentication yet.

### Step 1: SQLAlchemy ORM Models

Location: `database/models/`

Map each table in `schema.sql` to a SQLAlchemy `DeclarativeBase` model.
Order: `users` → `companies` → `jobs` → `applications` → `resumes` → `cover_letters`
(dependency order: FK targets first)

### Step 2: Alembic Setup

```bash
alembic init database/migrations
# Set sqlalchemy.url in alembic.ini to DATABASE_URL
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Verify: `alembic current` shows the head revision.

### Step 3: Repository Layer

Location: `backend/src/repositories/`

Implement concrete repositories implementing the Repository Protocols (`JobRepository`, `CompanyRepository`, `ApplicationRepository`, `UserRepository`).

Each repository:
- Accepts a SQLAlchemy `AsyncSession`
- Implements repository methods returning Pydantic models (not ORM models)
- Has integration tests in `tests/integration/repositories/`

### Step 4: Dependency Injection Setup

Set up a dependency injection container (or lightweight DI provider helpers) to inject concrete repository implementations into services. This ensures that services depend purely on the repository interfaces/protocols defined in `core/interfaces/repository.py`.

### Step 5: Service Layer

Location: `backend/src/services/`

Services orchestrate repositories. They contain business logic. Services are injected with repository protocols.
Order: `CompanyService` → `JobService` → `ResumeService` → `ApplicationService`
(`CompanyService` first because `JobService` depends on it for company resolution)

### Step 6: PersistenceStage Implementation

Location: `intelligence/pipeline/stages.py`

Now that repositories exist, implement `PersistenceStage.process()`.
This is the first pipeline stage to have real code.
Test: integration test that passes a Job through PersistenceStage and reads it back from the DB.

### Step 7: FastAPI Application

Location: `backend/src/main.py`, `backend/src/api/`

Add FastAPI app entry point. Add route groups:
- `GET /api/v1/jobs` — search and list
- `GET /api/v1/jobs/{id}` — job detail
- `POST /api/v1/applications` — create application
- `GET /api/v1/applications` — list user applications

**FastAPI comes last in Phase 2** — it exposes the service layer, not the other way around. Authentication is deferred until the core functions are validated via Swagger.

### Step 8: OpenAPI Validation

```bash
uvicorn backend.src.main:app --reload
# Visit http://localhost:8000/docs
```

Verify: all endpoints have request/response schemas in the OpenAPI spec.

**Phase 2 Definition of Done:**
- [ ] Alembic migrations run cleanly on a fresh database
- [ ] All repositories have integration tests passing
- [ ] `POST /api/v1/jobs` stores a job in the DB
- [ ] `GET /api/v1/jobs` returns that job
- [ ] OpenAPI spec is complete and valid
- [ ] No hardcoded SQL strings — all queries via repositories

---

## Phase 3 — Connector Queue & Greenhouse Ingestion

**Objective:** Validate the entire ingestion pipeline asynchronously with exactly one production-grade connector (Greenhouse).

### Step 1: Queue Abstraction (Milestone 3.1)
- Introduce a queue broker interface (using Redis backing with RQ, Celery, or Arq).
- Establish queueing operations for event worker dispatch.

### Step 2: Event Bus (Milestone 3.2)
- Implement event publisher, subscriber, automatic retry on transient failure, and a Dead-Letter Queue (DLQ) for dead events.

### Step 3: Greenhouse Connector (Milestone 3.3)
- Implement concrete `GreenhouseConnector(BaseConnector)`. Register via registry.
- Target only Greenhouse public API endpoints (JSON).

### Step 4: Normalizer Stage (Milestone 3.4)
- Implement `NormalizerStage` to parse and validate Greenhouse payloads into universal `Job` format.

### Step 5: Company Resolver Stage (Milestone 3.5)
- Reuse the implemented `CompanyResolverStage` (Stage 3) to normalize company name and match/create company profiles.

### Step 6: Persistence Stage (Milestone 3.6)
- Reuse the implemented `PersistenceStage` (Stage 6) to upsert jobs and link company IDs.

### Step 7: End-to-End Integration Test (Milestone 3.7)
- Write integration tests verifying:
  `Greenhouse API (fixture) -> Connector -> JobDiscovered Event -> Ingestion Queue -> Pipeline (Normalizer -> CompanyResolver -> Persistence) -> DB`.

**Phase 3 Definition of Done:**
- [ ] Greenhouse connector operational against real/recorded API payloads
- [ ] Redis-backed queue handles asynchronous job scheduling
- [ ] Full pipeline resolves/creates company, normalizes job data, and persists records
- [ ] End-to-end integration test passes successfully in CI environment

---

## Phase 4 — Connector Framework Validation

**Objective:** Standardize and robustly validate the ingestion engine across multiple connector sources (Greenhouse, Lever).

### Step 1: Lever Connector
- Implement concrete `LeverConnector(BaseConnector)` representing the Lever board schema.
- Exclude logic other than search, fetch, and health check.

### Step 2: Compare Schema Output
- Verify that Greenhouse and Lever adapters produce identical format universal `Job` objects after normalization.

### Step 3: Health Monitoring & Metrics
- Extend `ConnectorRunner` to update connector health metrics in the database (`ConnectorHealthORM`, `ConnectorRunORM`) including latency, success rate, and error counters.

### Step 4: Retry Policies
- Categorize permanent vs transient errors. Implement automatic retry policy for transient errors (e.g. timeout, 5xx) and skip retries on permanent errors (e.g. 404).

### Step 5: Dead Letter Queue (DLQ)
- Route repeatedly failing payloads to a dedicated DLQ table/log rather than silently dropping them.

**Phase 4 Definition of Done:**
- [ ] Greenhouse and Lever connectors operational
- [ ] ConnectorRunner writes latency/success telemetry to the DB
- [ ] Failed runs trigger retries or DLQ logging
- [ ] Integration tests verify identical normalized outputs for both connectors

---

## Phase 5 — Scheduler + Redis Event Bus

**Objective:** Automate connector execution asynchronously with cron schedules.
- Introduce APScheduler / Redis queue backing for async processing.
- Boot background scheduler worker.

---

## Phase 6 — Intelligence

**Objective:** cosine similarity, vectors, and fit ratings.
- cosine distance via pgvector.
- RankerStage implementations.
- Cosine-similarity fuzzy deduplication.

---

## Phase 7 — AI Engines

**Objective:** Generative engines for careers.
- Resume Builder & custom tailors.
- Cover Letter generation.
- Mock interview sessions.

---

## Phase 8 — Frontend

**Objective:** Clean user dashboard UI.
- Scaffolding Next.js App Router.
- Kanban style application tracker.

---

## Phase 9 — Notifications & Extensions

**Objective:** Aggregations and automation.
- SMTP email notifications.
- Browser extension for one-click application indexing.
- OAuth / JWT security.

---

## Key Rules (Never Break)

| Rule | Reason |
|------|--------|
| Repositories use Protocols | Clean dependency injection; mocks can easily replace real DB drivers |
| FastAPI after repositories | API exposes business logic — logic shouldn't be written around the framework |
| Frontend after stable API | Building both ends simultaneously causes constant churn at the boundary |
| One pipeline stage at a time | Each stage has a clear input/output contract; mix them and testing becomes impossible |
| Correlation IDs on all events | Required for distributed tracing; retrofitting is expensive |
| No SQL in service layer | All DB access via repositories — services stay testable without a DB |
| No business logic in API routes | Routes validate and delegate; logic lives in services |

