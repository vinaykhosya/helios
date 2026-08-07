# Helios v3.0 — Complete Junior-Engineer Implementation Plan

> **How to read this document**
> Every task has: **Goal → Inputs → Steps → Output → Test → Done When**
> Pick any uncompleted task, implement it, write the test, verify the Done When criteria, then move on.
> You never need to understand the whole system to contribute a single task.

---

## Repository Layout (Reference)

```
helios/
├── core/                    ← Universal contracts (models, interfaces, events). NEVER import from backend/ai/intelligence.
│   ├── models/              ← Pydantic v2 domain models (Job, Company, Application, User)
│   ├── interfaces/          ← Abstract base classes and Protocols
│   └── events/              ← Typed event definitions + in-process event bus
├── backend/src/
│   ├── connectors/          ← ATS connector implementations (Greenhouse, Lever, Ashby, Workday)
│   ├── repositories/        ← SQLAlchemy async repository implementations
│   ├── services/            ← Business logic services (JobService, ApplicationService, etc.)
│   ├── api/                 ← FastAPI route handlers
│   └── main.py              ← FastAPI app entry point
├── intelligence/
│   ├── pipeline/            ← 6-stage ingestion pipeline stages
│   ├── ranking/             ← Eligibility Gate + Ranking Agent
│   ├── deduplication/       ← Fuzzy deduplication algorithms
│   └── recommendation/      ← Career path recommendations
├── ai/
│   ├── providers/           ← LLM provider adapters (Anthropic, OpenAI, Ollama)
│   ├── engines/             ← Resume, CoverLetter, Reviewer, Interview, SkillGap engines
│   ├── memory/              ← Memory Service (shared stateful store)
│   └── prompts/             ← Prompt templates (separate from engine logic)
├── workers/                 ← Background workers (ingestion, ranking, notification)
├── automation/              ← Playwright browser automation agents
├── database/
│   ├── models/              ← SQLAlchemy ORM models
│   ├── migrations/          ← Alembic migration scripts
│   └── schema.sql           ← Reference SQL schema
├── shared/telemetry/        ← Logging, metrics, tracing helpers
├── docs/                    ← All architecture + implementation documentation
└── tests/                   ← Mirrors src structure: unit/ and integration/
```

---

## Dependency Rules (Never Break These)

```
core/           ← no runtime deps (only pydantic)
  ↑
backend/        ← depends on core + database drivers
ai/             ← depends on core + LLM provider SDKs
intelligence/   ← depends on core + ai/ (optionally)
workers/        ← depends on core + backend + intelligence
automation/     ← depends on core + ai/ + backend
```

---

# PHASE 0: Project Hygiene & Environment Setup
**Status: ✅ Largely complete — verify items below**

---

## Milestone 0.1 — Python environment verification
**Estimated time: 30 minutes**

### Task 0.1.1 — Verify all imports work
```
Goal: Confirm Phase 1 code is importable with zero circular imports.

Steps:
  1. Run: python -c "import core; import intelligence; import ai; print('OK')"
  2. If errors, trace the import chain and fix.

Done When: The command above prints OK with no errors.
```

### Task 0.1.2 — Verify test suite passes
```
Goal: Confirm all existing tests pass before any new work begins.

Steps:
  1. Run: pytest
  2. Expected: 36 passed, 7 skipped (skips are OK — they need a live DB)

Done When: pytest exits with 0 errors. All non-integration tests pass.
```

### Task 0.1.3 — Add .env configuration
```
Goal: Set up local environment variables needed by all future phases.

File to create: .env (copy from .env.example)

Required keys:
  DATABASE_URL=postgresql+asyncpg://helios:helios@localhost:5432/helios
  REDIS_URL=redis://localhost:6379/0
  OPENAI_API_KEY=sk-...
  ANTHROPIC_API_KEY=sk-ant-...
  TELEGRAM_BOT_TOKEN=...
  TELEGRAM_CHAT_ID=...
  ENVIRONMENT=development

Done When: .env file exists and is in .gitignore (already is).
```

---

# PHASE 1: Persistence Layer (SQLAlchemy + Alembic)
**Goal: Make jobs writable to and readable from a real PostgreSQL database.**
**Status: Schema defined (database/schema.sql). ORM models partially written. Repositories partially written.**

---

## Milestone 1.1 — SQLAlchemy ORM Models
**Location: `database/models/`**
**Estimated time: 3–4 hours**

### Task 1.1.1 — Verify base ORM model
```
Goal: Confirm database/models/base.py has a clean DeclarativeBase.

File: database/models/base.py

Must contain:
  from sqlalchemy.orm import DeclarativeBase
  class Base(DeclarativeBase): pass

Done When: python -c "from database.models.base import Base; print(Base)" works.
```

### Task 1.1.2 — Implement User ORM model
```
Goal: Map the users table from schema.sql to a SQLAlchemy model.

File: database/models/user.py

Columns to map (from schema.sql):
  id          UUID primary key
  email       VARCHAR(255) unique not null
  name        VARCHAR(255)
  settings    JSONB
  created_at  TIMESTAMPTZ default now()
  updated_at  TIMESTAMPTZ

Rules:
  - Use mapped_column() and Mapped[] type annotations (SQLAlchemy 2.0 style)
  - id should default to uuid4 on the Python side
  - settings should use JSON type

Example skeleton:
  class UserORM(Base):
      __tablename__ = "users"
      id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
      email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
      ...

Test: tests/unit/database/test_user_orm.py
  - Instantiate UserORM() with required fields
  - Assert tablename == "users"
  - Assert id is auto-generated

Done When: Test passes.
```

### Task 1.1.3 — Implement Company ORM model
```
Goal: Map the companies table.

File: database/models/company.py

Columns (from schema.sql):
  id              UUID primary key
  name            VARCHAR(255) not null
  name_normalized VARCHAR(255) unique
  website         VARCHAR(500)
  industry        VARCHAR(100)
  size_range      VARCHAR(50)
  created_at      TIMESTAMPTZ

Done When: Unit test instantiates CompanyORM and asserts tablename == "companies".
```

### Task 1.1.4 — Implement Job ORM model
```
Goal: Map the jobs table. This is the most important ORM model.

File: database/models/job.py

Columns (from schema.sql) — focus on these key ones:
  id              UUID primary key
  source          VARCHAR(50) not null (e.g. "greenhouse")
  source_id       VARCHAR(255) not null
  title           VARCHAR(500) not null
  company         VARCHAR(255)
  company_id      UUID FK → companies.id (nullable)
  location        VARCHAR(255)
  remote          BOOLEAN default false
  employment_type VARCHAR(50)
  description     TEXT
  skills          JSONB  (list of strings)
  salary_min      NUMERIC
  salary_max      NUMERIC
  salary_currency VARCHAR(10)
  fit_score       FLOAT
  apply_url       VARCHAR(1000)
  posted_at       TIMESTAMPTZ
  expires_at      TIMESTAMPTZ
  created_at      TIMESTAMPTZ

Constraints:
  - UNIQUE (source, source_id) — one record per portal job

ForeignKey setup:
  company_id = mapped_column(ForeignKey("companies.id"), nullable=True)

Done When: Unit test instantiates JobORM, asserts tablename == "jobs",
           asserts source + source_id uniqueness constraint exists.
```

### Task 1.1.5 — Implement Application ORM model
```
Goal: Map the applications table.

File: database/models/application.py

Key columns:
  id              UUID primary key
  user_id         UUID FK → users.id
  job_id          UUID FK → jobs.id
  status          VARCHAR(50) — "applied","interview","offer","rejected"
  confidence_score FLOAT
  applied_at      TIMESTAMPTZ
  resume_version  VARCHAR(100)
  notes           TEXT

Done When: Unit test passes.
```

---

## Milestone 1.2 — Alembic Migration Setup
**Location: `database/migrations/`**
**Estimated time: 1–2 hours**

### Task 1.2.1 — Configure alembic.ini
```
Goal: Connect Alembic to your local PostgreSQL database.

File: alembic.ini

Change this line:
  sqlalchemy.url = postgresql+asyncpg://helios:helios@localhost:5432/helios

Also update database/migrations/env.py:
  - Import all ORM models so Alembic can detect them
  - from database.models.base import Base
  - from database.models import user, company, job, application  # noqa (side-effect import)
  - target_metadata = Base.metadata

Done When: alembic check exits without errors (no DB needed for this).
```

### Task 1.2.2 — Generate and apply initial migration
```
Goal: Create the actual database tables.

Steps:
  1. Start PostgreSQL locally (docker-compose up db or local install)
  2. Create database: createdb helios
  3. Run: alembic revision --autogenerate -m "initial_schema"
  4. Inspect the generated file in database/migrations/versions/
     — confirm it creates users, companies, jobs, applications tables
  5. Run: alembic upgrade head

Done When:
  - alembic current shows head revision
  - SELECT table_name FROM information_schema.tables WHERE table_schema='public';
    shows: users, companies, jobs, applications
```

---

## Milestone 1.3 — Concrete Repository Implementations
**Location: `backend/src/repositories/`**
**Estimated time: 4–6 hours**

### Task 1.3.1 — Implement async database session factory
```
Goal: Create a reusable async SQLAlchemy session factory.

File: backend/src/core/database.py

Must contain:
  from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

  engine = create_async_engine(settings.DATABASE_URL, echo=False)
  AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

  async def get_db() -> AsyncGenerator[AsyncSession, None]:
      async with AsyncSessionLocal() as session:
          yield session

Done When: python -c "from backend.src.core.database import get_db" works.
```

### Task 1.3.2 — Implement JobRepository (SQLAlchemy)
```
Goal: Implement the JobRepository protocol using SQLAlchemy AsyncSession.

File: backend/src/repositories/job.py

Must implement all methods from core/interfaces/repository.py:JobRepository:
  - async create(job: Job) → Job
  - async get_by_id(job_id: str) → Optional[Job]
  - async get_by_source_id(source: str, source_id: str) → Optional[Job]
  - async update(job: Job) → Job
  - async delete(job_id: str) → bool
  - async list_jobs(limit, offset) → list[Job]

Key rule:
  - All DB queries go through SQLAlchemy — ZERO raw SQL strings allowed.
  - Repository returns Pydantic Job models, NOT ORM objects.
  - Use a mapper function: job_orm_to_domain(orm: JobORM) → Job

Test: tests/integration/repositories/test_job_repository.py
  @pytest.mark.asyncio
  async def test_create_and_retrieve_job(db_session):
      repo = SQLAlchemyJobRepository(db_session)
      job = Job(source="greenhouse", source_id="abc123", title="AI Engineer", company="Acme")
      created = await repo.create(job)
      found = await repo.get_by_source_id("greenhouse", "abc123")
      assert found is not None
      assert found.title == "AI Engineer"

Done When: Integration test passes against a real (local) database.
```

### Task 1.3.3 — Implement CompanyRepository
```
Goal: Implement CompanyRepository protocol.

File: backend/src/repositories/company.py

Methods:
  - create(company: Company) → Company
  - get_by_id(company_id: str) → Optional[Company]
  - get_by_normalized_name(name_normalized: str) → Optional[Company]
  - update(company: Company) → Company
  - list_companies(limit, offset) → list[Company]

Note: get_by_normalized_name is critical for CompanyResolverStage.
  It must do a case-insensitive exact match on name_normalized column.

Done When: Integration test passes.
```

### Task 1.3.4 — Implement ApplicationRepository
```
Goal: Implement ApplicationRepository protocol.

File: backend/src/repositories/application.py

Methods:
  - create(application: Application) → Application
  - get_by_id(application_id: str) → Optional[Application]
  - get_by_user_and_job(user_id: str, job_id: str) → Optional[Application]
  - update(application: Application) → Application
  - list_by_user(user_id: str) → list[Application]

Done When: Integration test creates an application and retrieves it by user+job IDs.
```

---

## Milestone 1.4 — FastAPI Application Shell
**Location: `backend/src/`**
**Estimated time: 2–3 hours**

### Task 1.4.1 — Wire up FastAPI app with DI
```
Goal: Create a running FastAPI app with dependency injection for repositories.

File: backend/src/main.py

Required:
  app = FastAPI(title="Helios API", version="1.0.0")

  @app.get("/health")
  async def health(): return {"status": "ok"}

  app.include_router(jobs_router, prefix="/api/v1")
  app.include_router(applications_router, prefix="/api/v1")

Done When: uvicorn backend.src.main:app --reload starts without errors.
           GET http://localhost:8000/health returns {"status":"ok"}
```

### Task 1.4.2 — Implement Jobs API routes
```
Routes:
  GET    /api/v1/jobs              → list_jobs(limit, offset)
  GET    /api/v1/jobs/{id}         → get_job_by_id
  POST   /api/v1/jobs              → create_job (admin)

Done When: All 3 routes return correct JSON. Verified via Swagger at /docs.
```

### Task 1.4.3 — Implement Applications API routes
```
Routes:
  GET  /api/v1/applications         → list applications for current user
  POST /api/v1/applications         → create application record
  PUT  /api/v1/applications/{id}    → update status

Done When: Routes return correct JSON. Verified via Swagger at /docs.
```

---

# PHASE 2: Connector SDK — The Plugin Architecture
**Goal: Make adding a new ATS connector a 1-file job.**
**Status: BaseConnector exists. Greenhouse + Lever implemented. Ashby + Workday needed.**

---

## Milestone 2.1 — Finalize Connector SDK Interface

### Task 2.1.1 — Extend BaseConnector with apply() and check_status()
```
Goal: Every ATS connector must support applying and checking application status.

File: core/interfaces/connector.py

Add these abstract methods:

  @abstractmethod
  async def apply(
      self,
      job: Job,
      resume_path: str,
      cover_letter_path: str,
      candidate_profile: "CandidateProfile",
  ) -> "ApplicationResult":
      """
      Submit an application.

      Returns ApplicationResult with:
        - success: bool
        - confirmation_id: Optional[str]
        - requires_human: bool
        - pause_reason: Optional[str]  (e.g. "CAPTCHA", "OTP_REQUIRED")
      """
      ...

  @abstractmethod
  async def check_status(self, confirmation_id: str) -> "ApplicationStatus":
      """
      Returns: PENDING, UNDER_REVIEW, REJECTED, INTERVIEW, OFFER
      """
      ...

Also create: core/models/application_result.py
  class ApplicationResult(BaseModel):
      success: bool
      confirmation_id: Optional[str] = None
      requires_human: bool = False
      pause_reason: Optional[str] = None
      error_message: Optional[str] = None

Done When: Greenhouse/Lever connectors still import cleanly after this change.
```

### Task 2.1.2 — Write Connector SDK documentation
```
File: docs/connector_sdk.md

Must cover:
  1. What is a connector?
  2. The 6 methods to implement
  3. How to register in ConnectorRegistry
  4. Copy-paste skeleton
  5. How to write a fixture-based test
  6. Common pitfalls

Done When: A new engineer can add a connector following this doc alone.
```

---

## Milestone 2.2 — Ashby Connector
**Estimated time: 4–6 hours**

### Task 2.2.1 — Research Ashby API + create fixture
```
Steps:
  1. Read: https://developers.ashbyhq.com/reference
  2. Capture a real Ashby job board response
  3. Save realistic fixture: tests/fixtures/ashby_job_payload.json

Done When: Fixture exists with sample Ashby job data.
```

### Task 2.2.2 — Implement AshbyConnector
```
File: backend/src/connectors/ashby.py

Ashby API pattern:
  GET https://api.ashbyhq.com/posting-api/job-board/{company_slug}

Field mapping:
  id              → source_id
  title           → title
  location.name   → location
  descriptionHtml → description
  isRemote        → remote
  employmentType  → employment_type
  applyUrl        → apply_url
  publishedDate   → posted_at

Tests:
  - test_normalize_maps_fields (use fixture, no HTTP)
  - test_search_returns_jobs (mock httpx)
  - test_health_check_returns_true (mock HTTP 200)

Done When: All 3 tests pass.
```

### Task 2.2.3 — Register AshbyConnector in ConnectorRegistry
```
File: backend/src/connectors/registry.py
Add: "ashby": AshbyConnector

Done When: registry.get("ashby") returns an AshbyConnector instance.
```

---

## Milestone 2.3 — Workday Connector
**Estimated time: 6–8 hours**

### Task 2.3.1 — Research Workday API structure
```
Steps:
  1. Open any Workday job board in Chrome DevTools
  2. Capture the undocumented REST API pattern:
     POST /wday/cxs/{tenant}/{jobBoardId}/jobs
  3. Document in: docs/workday_api_notes.md
  4. Create fixture: tests/fixtures/workday_job_payload.json

Done When: You can reproduce a job search via httpx manually.
```

### Task 2.3.2 — Implement WorkdayConnector.search()
```
File: backend/src/connectors/workday.py

WorkdayConnector takes (tenant_name, board_id) at init.
Implements pagination with offset+limit.

Done When: Unit test with mocked httpx returns list of Job objects.
```

### Task 2.3.3 — Implement WorkdayConnector.normalize()
```
Common Workday fields:
  title               → title
  externalUrl         → apply_url
  locationsText       → location
  postedDate          → posted_at

Done When: Unit test using fixture data returns a valid Job.
```

---

# PHASE 3: Eligibility Gate
**Goal: Fast binary filter — "Can Vinay legally and practically apply?"**
**Status: Not started.**

---

## Milestone 3.1 — Candidate Preference Model

### Task 3.1.1 — Create CandidateProfile model
```
File: core/models/candidate_profile.py

class CandidateProfile(BaseModel):
    name: str
    email: str
    location: str
    willing_to_relocate: bool = True
    requires_sponsorship: bool = False
    graduation_year: int
    years_of_experience: float

    # Hard constraints
    min_salary: Optional[float] = None
    max_experience_years: float = 3.0
    required_tech_stack: list[str] = []
    excluded_keywords: list[str] = []
    target_locations: list[str] = []
    excluded_companies: list[str] = []
    job_types: list[str] = ["full_time"]

    # Soft preferences (for Ranking Agent)
    preferred_company_sizes: list[str] = []
    preferred_industries: list[str] = []
    ideal_role_keywords: list[str] = []

Done When: Import works. Unit test creates instance with all fields.
```

### Task 3.1.2 — Create candidate_profile.yaml + loader
```
File: config/candidate_profile.yaml  (filled with your actual preferences)
File: core/config/profile_loader.py  (load_candidate_profile() function)

Done When: load_candidate_profile() returns a valid CandidateProfile.
```

---

## Milestone 3.2 — Eligibility Gate Implementation

### Task 3.2.1 — Implement EligibilityGate with 7 rules
```
File: intelligence/ranking/eligibility.py

class EligibilityResult(BaseModel):
    eligible: bool
    rejection_reasons: list[str]

class EligibilityGate:
    def check(self, job: Job) -> EligibilityResult: ...

Rules (in order, fast-fail):
  1. EXCLUDED_KEYWORDS_IN_TITLE: any excluded_keyword in job.title
  2. EXCLUDED_KEYWORDS_IN_DESCRIPTION: any excluded_keyword in job.description
  3. EXCLUDED_COMPANY: job.company in excluded_companies
  4. REQUIRED_TECH_STACK: none of required_tech_stack found in job
  5. LOCATION: job not remote AND job.location not in target_locations
  6. EXPERIENCE_RANGE: parsed min experience from JD > max_experience_years
     (use regex: r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s+)?experience")
  7. EMPLOYMENT_TYPE: job.employment_type not in profile.job_types

Tests (one per rule minimum):
  - test_passes_valid_job
  - test_rejects_excluded_keyword_in_title
  - test_rejects_excluded_keyword_in_description
  - test_rejects_excluded_company
  - test_rejects_missing_required_tech
  - test_rejects_wrong_location
  - test_rejects_experience_too_high
  - test_rejects_wrong_employment_type

Done When: All 8 tests pass. Zero LLM calls. Zero async operations.
```

### Task 3.2.2 — Batch filter + rejection stats
```
File: intelligence/ranking/eligibility.py (extend)

  async def filter_batch(jobs) -> tuple[list[Job], list[EligibilityResult]]: ...
  def summarize_session(results) -> RejectionStats: ...

class RejectionStats(BaseModel):
    total_scanned: int
    total_eligible: int
    rejection_counts: dict[str, int]

Done When: filter_batch on 1000 jobs completes in < 1 second.
```

---

# PHASE 4: Ranking Agent
**Goal: Multi-dimensional soft scoring — "Should Vinay apply?"**

---

## Milestone 4.1 — Skill Vector Matching

### Task 4.1.1 — Build keyword-based SkillExtractor
```
File: intelligence/ranking/skill_extractor.py

KNOWN_SKILLS list of 80+ tech keywords.
extract_from_job(job) → list[str]  (case-insensitive scan of title+description+skills)
extract_from_profile(profile) → list[str]

Done When: Unit test extracts correct skills from realistic JD text.
```

### Task 4.1.2 — Implement SkillMatchScorer
```
File: intelligence/ranking/skill_match_scorer.py

class SkillMatchScore(BaseModel):
    overall_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    breakdown: dict[str, float]

Formula: score = len(matched) / max(len(job_skills), 1)

Test:
  job_skills = ["Python", "Docker", "LLM", "FastAPI"]
  candidate = ["Python", "LLM", "FastAPI"]
  score = 0.75, missing = ["Docker"]

Done When: Test passes with correct scores.
```

---

## Milestone 4.2 — RankingAgent

### Task 4.2.1 — Implement MatchDimension + RankingResult models
```
File: intelligence/ranking/ranker.py

class MatchDimension(BaseModel):
    name: str
    score: float
    weight: float
    matched: bool

class RankingResult(BaseModel):
    job_id: str
    overall_score: float
    confidence: float
    dimensions: list[MatchDimension]
    missing_skills: list[str]
    recommendation: str   # "auto_apply" | "ask_user" | "review"
    reason: str
```

### Task 4.2.2 — Implement RankingAgent.rank()
```
File: intelligence/ranking/ranker.py

Dimensions to score:
  1. Tech Stack Match (weight: 0.40) — from SkillMatchScorer
  2. Location Match (weight: 0.20) — job.remote OR location in target_locations
  3. Seniority Match (weight: 0.20) — parse years from JD, compare to experience
  4. Role Keyword Match (weight: 0.20) — ideal_role_keywords in job title/description

Overall score = weighted average of dimensions.
Confidence = min(overall * 1.1, 1.0)

Recommendation thresholds:
  confidence ≥ 0.95 → "auto_apply"
  confidence ≥ 0.80 → "ask_user"
  else              → "review"

Tests:
  - test_high_match_gets_auto_apply
  - test_partial_match_gets_ask_user
  - test_poor_match_gets_review
  - test_dimension_weights_sum_correctly
  - test_missing_skills_identified

Done When: All 5 tests pass. No LLM calls.
```

### Task 4.2.3 — Wire RankingAgent into RankerStage
```
File: intelligence/pipeline/stages.py

RankerStage.process() should call self._ranking_agent.rank(job)
and set job.fit_score = result.overall_score

Done When: pytest passes without NotImplementedError from RankerStage.
```

---

# PHASE 5: Memory Service
**Goal: Shared persistent brain across all agents.**

---

## Milestone 5.1 — Memory Service Core

### Task 5.1.1 — Define MemoryService interface
```
File: ai/memory/service.py

Key methods:
  async has_applied(job_id, user_id) → bool
  async record_application(job_id, user_id, confirmation_id, resume_version, confidence_score) → None
  async get_standard_answer(question_text) → Optional[str]
  async store_standard_answer(question_text, answer) → None
  async record_resume_outcome(resume_version, company_type, outcome) → None
  async get_best_resume_version(company_type) → Optional[str]
  async get_rejection_stats(days=30) → dict
```

### Task 5.1.2 — Implement has_applied() with Redis cache
```
Pattern:
  cache_key = f"applied:{user_id}:{job_id}"
  1. Check Redis → return True if found
  2. Fall back to ApplicationRepository.get_by_user_and_job()
  3. If found in DB → warm Redis cache for 90 days

Tests (with mocked Redis + repo):
  - test_returns_true_from_cache
  - test_hits_db_on_cache_miss
  - test_warms_cache_after_db_hit
  - test_returns_false_for_new_job
```

### Task 5.1.3 — Implement questionnaire answer store
```
Question hashing:
  key = hashlib.sha256(question.lower().strip().encode()).hexdigest()[:16]
  redis.set(f"qa:{key}", answer)  # No expiry

Tests:
  - store + retrieve same question
  - different question returns None
  - case-insensitive retrieval
```

---

# PHASE 6: Resume Tailoring Agent

---

## Milestone 6.1 — Profile Intelligence Agent

### Task 6.1.1 — Create ProfileIntelligenceAgent
```
File: ai/engines/profile_intelligence.py

class ProfileIntelligenceAgent:
    def get_profile(self) → CandidateProfile
    def get_skills_for_job(self, job) → list[str]  (reorder by JD relevance)
    def get_experience_bullets(self, job) → list[str]

Done When: Instantiates from config/candidate_profile.yaml.
```

---

## Milestone 6.2 — Headless LaTeX PDF Compiler

### Task 6.2.1 — LaTeX template renderer
```
File: ai/engines/resume/latex_renderer.py

class LaTeXRenderer:
    def render(self, template_path: str, variables: dict) → str:
        """Replace {{VARIABLE_NAME}} tokens in template."""

Variables supported:
  {{CANDIDATE_NAME}}, {{CANDIDATE_EMAIL}}, {{COMPANY_NAME}},
  {{JOB_TITLE}}, {{PROFILE_STATEMENT}}, {{EXPERIENCE_BULLETS}},
  {{SKILLS_LIST}}, {{VERSION_TAG}}

Done When: render() replaces all tokens in cv/main_example.tex.
```

### Task 6.2.2 — Implement headless PDF compiler
```
File: ai/engines/resume/pdf_compiler.py

class PDFCompiler:
    async def compile(self, latex_content: str, output_name: str) → str:
        """
        1. Write to temp .tex file
        2. Run: lualatex --interaction=nonstopmode ...
        3. Timeout: 60 seconds
        4. Clean temp files
        5. Return path to .pdf
        Raises: PDFCompilationError on non-zero exit
        """

Tests (mocked subprocess):
  - test_calls_lualatex_with_correct_args
  - test_raises_on_compile_failure
  - test_returns_correct_output_path
```

### Task 6.2.3 — LLM bullet point generator
```
File: ai/engines/resume/bullet_generator.py

class BulletGenerator:
    async def generate_profile_statement(candidate, job) → str
        (2-3 sentences, ≤60 words, no buzzwords, third person)
    async def tailor_bullets(original_bullets, job, max_bullets=5) → list[str]

Done When: Unit test with mocked LLM returns formatted strings.
```

### Task 6.2.4 — ResumeTailoringAgent orchestrator
```
File: ai/engines/resume/tailor.py

Orchestrates: ProfileIntelligence → BulletGenerator → LaTeXRenderer → PDFCompiler
async def generate(job) → str (absolute path to PDF)

Done When: End-to-end test (mocked LLM + subprocess) returns a valid PDF path.
```

---

# PHASE 7: Application Agent (Playwright Browser Automation)

---

## Milestone 7.1 — Playwright Setup

### Task 7.1.1 — Create automation package
```
Add to pyproject.toml:
  automation = ["playwright>=1.45.0", "python-telegram-bot>=21.0"]

Run: pip install -e ".[automation]" && playwright install chromium

File: automation/browser.py
  class BrowserSession:  (async context manager returning a Playwright Page)

Done When: Manual test navigates to google.com without error.
```

---

## Milestone 7.2 — Confidence Engine

### Task 7.2.1 — Implement ConfidenceEngine
```
File: automation/confidence.py

class ApplicationDecision(str, Enum):
    AUTO_APPLY = "auto_apply"
    ASK_USER   = "ask_user"
    REVIEW     = "review"

class ConfidenceEngine:
    def decide(self, ranking_result, form_complexity=0) → ApplicationDecision:
        adjusted = ranking_result.confidence - (form_complexity * 0.05)
        if adjusted >= 0.95: return AUTO_APPLY
        elif adjusted >= 0.80: return ASK_USER
        else: return REVIEW

Tests:
  - high confidence + standard form → AUTO_APPLY
  - borderline + custom questions → ASK_USER
  - low confidence → REVIEW
```

---

## Milestone 7.3 — Greenhouse Form Filler
**Hardest technical task in the project.**

### Task 7.3.1 — Map Greenhouse form HTML structure
```
Steps:
  1. Open any boards.greenhouse.io/company job
  2. Inspect each form field (id, name, aria-label)
  3. Document in: docs/greenhouse_form_mapping.md

Fields to map:
  First Name, Last Name, Email, Phone, Resume upload,
  Cover Letter upload, LinkedIn, Authorization radios, Custom questions
```

### Task 7.3.2 — Implement GreenhouseFormFiller
```
File: automation/fillers/greenhouse.py

class PauseRequired(Exception):
    def __init__(self, reason: str, screenshot_path: str): ...

class GreenhouseFormFiller:
    async def fill(page, job, candidate, resume_path, cover_letter_path) → bool

Methods:
  _fill_standard_fields(page, candidate)
    - Try multiple selectors for each field (id → name → aria-label)
  _upload_resume(page, resume_path)
  _upload_cover_letter(page, cover_letter_path)
  _fill_work_authorization(page, candidate)
  _handle_custom_questions(page, candidate)
    - Check MemoryService for known answer
    - Raise PauseRequired if unknown
  _detect_captcha(page) → bool
    - Check for recaptcha/hcaptcha iframes

Tests:
  - test_fills_standard_fields_correctly
  - test_raises_pause_on_captcha
  - test_raises_pause_on_unknown_question
  - test_uses_memory_for_known_questions

Done When: Tests pass. Manual visual test fills a real form (headless=False).
```

---

## Milestone 7.4 — Human-in-the-Loop Notification Bot

### Task 7.4.1 — Implement TelegramNotifier
```
File: automation/notification.py

class TelegramNotifier:
    async def send_approval_request(job, ranking_result, pause_reason=None) → str (pending_id)
    async def wait_for_response(pending_id, timeout_seconds=3600) → bool

Message format:
  🔔 Helios — Approval Required

  📋 Job: {job.title}
  🏢 Company: {job.company}
  🎯 Match: {score}%

  ✅ Matched: Python, LLM, FastAPI
  ❌ Missing: Docker

  [✅ Approve & Apply]  [❌ Skip]

Done When: Bot sends message. Clicking Approve returns True.
```

---

## Milestone 7.5 — Lever Form Filler

### Task 7.5.1 — Map Lever form structure
```
File: docs/lever_form_mapping.md
Lever boards: jobs.lever.co/company/job-id
```

### Task 7.5.2 — Implement LeverFormFiller
```
File: automation/fillers/lever.py
Same interface as GreenhouseFormFiller.

Done When: Tests pass. Manual visual test fills a Lever form.
```

---

## Milestone 7.6 — ApplicationAgent Orchestrator

### Task 7.6.1 — Implement ApplicationAgent
```
File: automation/application_agent.py

async def apply(job, ranking_result) → ApplicationOutcome:
  1. memory.has_applied() → skip if True
  2. confidence_engine.decide() → skip if REVIEW
  3. resume_agent.generate(job) → get resume PDF
  4. Get correct filler by ATS type (greenhouse/lever/ashby/workday)
  5. async with BrowserSession() as page:
       try: filler.fill(page, ...)
       if ASK_USER: notifier.send_approval_request() → wait → submit or skip
       except PauseRequired: notify user → manual handling
  6. memory.record_application()
  7. Return ApplicationOutcome

Done When: Integration test against a test HTML form confirms memory is written.
```

---

# PHASE 8: Workflow Orchestrator + Retry Engine

---

## Milestone 8.1 — WorkflowOrchestrator

### Task 8.1.1 — Implement event-driven orchestrator
```
File: workers/orchestrator.py

class WorkflowOrchestrator:
    Listens to: JobsDiscovered → triggers Eligibility → Ranking → ResumeTailoring → Apply
    Publishes: ApplicationQueued, BatchComplete

    async def on_jobs_discovered(event: JobsDiscovered):
        eligible, stats = await eligibility_gate.filter_batch(event.jobs)
        for job in eligible:
            result = ranking_agent.rank(job)
            if result.recommendation != "review":
                await application_agent.apply(job, result)

Done When: Unit test: publish JobsDiscovered → ApplicationAgent.apply() is called.
```

---

## Milestone 8.2 — Retry Engine

### Task 8.2.1 — Exponential backoff retry + DLQ
```
File: workers/retry_engine.py

MAX_ATTEMPTS = 3
BACKOFF = [60, 300, 900]  # seconds

async def schedule_retry(job, ranking_result, attempt, error):
    if attempt >= MAX_ATTEMPTS:
        await _send_to_dlq(job, error)
        return
    # Store in Redis with TTL for delayed requeue

Tests:
  - test_schedules_with_correct_delay
  - test_routes_to_dlq_after_max_attempts
  - test_dlq_entry_contains_error_details
```

---

# PHASE 9: Discovery Scheduler

---

## Milestone 9.1 — APScheduler

### Task 9.1.1 — 6-hour discovery scheduler
```
File: workers/scheduler.py

Uses APScheduler AsyncIOScheduler.
Runs _run_discovery_cycle() every 6 hours.
First run immediately on start.

Discovery cycle:
  1. For each connector: connector.search(queries, locations)
  2. Collect all → publish JobsDiscovered
  3. Orchestrator handles rest

Done When: Scheduler runs for 10 seconds without errors.
```

---

# PHASE 10: Tracking Agent + Gmail Scanner

---

## Milestone 10.1 — Gmail Inbox Scanner

### Task 10.1.1 — Gmail API auth setup
```
File: workers/gmail_auth.py
OAuth flow → token.json

Done When: Can list 10 most recent inbox emails.
```

### Task 10.1.2 — Email classifier
```
File: workers/tracking_agent.py

class EmailClassifier:
    CATEGORIES = {
        "application_received": ["application received", "thank you for applying"],
        "interview_invite": ["interview", "schedule a call"],
        "rejection": ["unfortunately", "not moving forward"],
        "online_assessment": ["online assessment", "coding challenge", "hackerrank"],
        "offer": ["offer letter", "pleased to offer"],
    }
    def classify(self, subject, body) → str

Done When: Unit tests cover all categories with realistic email text.
```

### Task 10.1.3 — ApplicationTracker
```
Matches email company name to open applications.
Updates application status in DB.
Writes outcome to Memory Service.
Triggers interview prep if status == "interview_scheduled".

Done When: Integration test updates status from "applied" to "interview_scheduled".
```

---

# PHASE 11: Observability + Daily Briefing

---

## Milestone 11.1 — Session Metrics

### Task 11.1.1 — HeliosSessionMetrics model
```
File: shared/telemetry/metrics.py

class HeliosSessionMetrics(BaseModel):
    session_id: str
    started_at: datetime
    jobs_scanned: int = 0
    jobs_eligible: int = 0
    rejection_reasons: dict[str, int] = {}
    applied: int = 0
    auto_applied: int = 0
    awaiting_approval: int = 0
    failed: int = 0
    avg_application_time_seconds: float = 0.0
    new_interviews: int = 0
    new_rejections: int = 0
```

---

## Milestone 11.2 — Morning Briefing Generator

### Task 11.2.1 — MorningBriefingGenerator
```
File: workers/briefing.py

async def generate(metrics, upcoming_interviews, memory) → str

Output format:
  ☀ Good morning Vinay — Thursday, 07 August 2026

  Yesterday Helios:
    ✓ Scanned    3,248 job postings
    ✓ Eligible      87
    ✓ Excellent     11 matches (≥85%)
    ✓ Applied        7 (auto)
    ⏳ Awaiting      2
    ⚠  Paused        1 (CAPTCHA)

  Rejections:
    72 → Experience > 5 years
    31 → Wrong tech stack
    18 → Location mismatch

  🗓 Siemens — tomorrow 2pm

  Best resume: v14-ml-focus
  Avg time per application: 31 seconds

Done When: Unit test generates briefing from sample metrics with all fields present.
```

---

# PHASE 12: Company Intelligence

---

## Milestone 12.1 — CompanyIntelligenceAgent

### Task 12.1.1 — Implement company research + dossier
```
File: ai/engines/company_intelligence.py

class CompanyDossier(BaseModel):
    company_name: str
    mission_statement: str
    tech_stack: list[str]
    recent_news: list[str]
    glassdoor_rating: Optional[float]
    likely_interview_questions: list[str]
    culture_keywords: list[str]
    competitors: list[str]
    products: list[str]

class CompanyIntelligenceAgent:
    async def research(self, company: str, role: str) → CompanyDossier:
        1. Web search for "{company} tech stack"
        2. Web search for "{company} news last 30 days"
        3. Web search for "{company} Glassdoor"
        4. LLM synthesizes into CompanyDossier
        5. LLM generates likely interview questions

Done When: research("Siemens", "AI Engineer") returns populated CompanyDossier.
```

---

# APPENDIX A: Testing Standards

```
tests/
  unit/                     ← Fast. No DB. No network. All deps mocked.
    ai/
      memory/               ← test_memory_service.py
      engines/resume/       ← test_tailor.py, test_pdf_compiler.py
    intelligence/ranking/   ← test_eligibility.py, test_ranker.py
    automation/             ← test_greenhouse_filler.py, test_confidence.py
    workers/                ← test_orchestrator.py, test_briefing.py
  integration/              ← Requires live DB + Redis
    repositories/           ← test_job_repository.py
    automation/             ← test_greenhouse_live.py (@pytest.mark.live)
```

**Common fixtures to add in conftest.py:**
- `async_db_session` — real AsyncSession for integration tests
- `mock_memory` — MagicMock(MemoryService)
- `sample_job` — a valid Job instance
- `sample_profile` — a valid CandidateProfile

---

# APPENDIX B: Component Status Tracker

| Phase | Component | Status | Priority |
|-------|-----------|--------|----------|
| 1 | SQLAlchemy ORM Models | 🔶 Partial | HIGH |
| 1 | Alembic Migrations | 🔶 Setup started | HIGH |
| 1 | Repository Implementations | 🔶 Partial | HIGH |
| 1 | FastAPI Routes | 🔶 Basic shell | MEDIUM |
| 2 | BaseConnector.apply() method | 🔴 Not started | HIGH |
| 2 | Ashby Connector | 🔴 Not started | HIGH |
| 2 | Workday Connector | 🔴 Not started | MEDIUM |
| 3 | CandidateProfile model | 🔴 Not started | HIGH |
| 3 | EligibilityGate (7 rules) | 🔴 Not started | HIGH |
| 4 | SkillExtractor + Scorer | 🔴 Not started | HIGH |
| 4 | RankingAgent | 🔴 Not started | HIGH |
| 5 | MemoryService | 🔴 Not started | HIGH |
| 6 | ProfileIntelligenceAgent | 🔴 Not started | HIGH |
| 6 | LaTeXRenderer | 🔴 Not started | HIGH |
| 6 | PDFCompiler | 🔴 Not started | HIGH |
| 6 | BulletGenerator | 🔴 Not started | HIGH |
| 6 | ResumeTailoringAgent | 🔴 Not started | HIGH |
| 7 | Playwright setup | 🔴 Not started | HIGH |
| 7 | ConfidenceEngine | 🔴 Not started | HIGH |
| 7 | GreenhouseFormFiller | 🔴 Not started | HIGH |
| 7 | LeverFormFiller | 🔴 Not started | HIGH |
| 7 | TelegramNotifier | 🔴 Not started | HIGH |
| 7 | ApplicationAgent | 🔴 Not started | HIGH |
| 8 | WorkflowOrchestrator | 🔴 Not started | MEDIUM |
| 8 | RetryEngine | 🔴 Not started | MEDIUM |
| 9 | APScheduler (6h discovery) | 🔴 Not started | MEDIUM |
| 10 | Gmail Inbox Scanner | 🔴 Not started | LOW |
| 10 | ApplicationTracker | 🔴 Not started | LOW |
| 11 | SessionMetrics | 🔴 Not started | LOW |
| 11 | MorningBriefingGenerator | 🔴 Not started | LOW |
| 12 | CompanyIntelligenceAgent | 🔴 Not started | LOW |

---

# APPENDIX C: MVP Completion Criteria

**Helios is genuinely useful when this single flow works end-to-end:**

```
1. HeliosScheduler fires → Greenhouse connector fetches 50 new jobs
       ↓
2. EligibilityGate filters → 5 pass hard rules
       ↓
3. RankingAgent scores → 2 score ≥ 80%
       ↓
4. ResumeTailoringAgent generates → 2 tailored ATS-optimized PDFs
       ↓
5. ApplicationAgent fills Greenhouse form → 1 auto-applied, 1 → Telegram
       ↓
6. MemoryService records → no duplicates on next run
       ↓
7. MorningBriefingGenerator sends → Telegram message at 08:00
```

**Every phase in this document serves this 7-step flow.**
When this works, everything else is iteration.
