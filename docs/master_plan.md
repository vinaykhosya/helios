# Master Implementation Plan & Architectural Roadmap

## Executive Summary & Product Vision

**Helios** is an end-to-end, enterprise-grade **AI Career Intelligence & Job Search Automation Platform**. It automates the complete candidate lifecycle:
1. **Multi-Portal Ingestion**: Scrapes and fetches job postings continuously across public board APIs (Greenhouse, Lever, LinkedIn, Jobnet, Jobbank, Jobindex, Jobdanmark).
2. **Normalized Intelligence Pipeline**: Cleans, deduplicates, resolves company profiles, computes vector embeddings, and ranks job matches against candidate profiles using `pgvector` and LLM scoring.
3. **Generative Application Suite**: Automated tailoring of LaTeX CVs, customized cover letters, AI reviewer critique loops, interview preparation simulators, and skill gap learning plans.
4. **CRM & Automated Tracking**: Kanban application pipeline, scheduled background execution, dead-letter queues, real-time telemetry, and multi-channel notifications (email, push, browser extension).

---

## Deployed GitHub Repository

- **Public Repository**: [https://github.com/vinaykhosya/helios](https://github.com/vinaykhosya/helios)
- **License**: MIT
- **Architecture**: Layered Monorepo (Python 3.11+ / Pydantic v2 / FastAPI / SQLAlchemy 2.0 / PostgreSQL 15 + pgvector / Redis / Next.js)

---

## Architectural Overview & Component Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            HELIOS PLATFORM                                  │
│                                                                             │
│  ┌──────────────┐     ┌──────────────────────────────────────────────────┐  │
│  │   Frontend   │     │                   Backend                        │  │
│  │  (Next.js)   │◄───►│  ┌───────────┐   ┌────────────────────────────┐  │  │
│  │  /dashboard  │     │  │    API    │   │         Services           │  │  │
│  │  /jobs       │     │  │  Routes   │   │ JobService, ApplicationSvc │  │  │
│  │  /applications     │  └─────┬─────┘   │ ResumeSvc, CompanySvc      │  │  │
│  │  /analytics  │     │        │         └─────────────┬──────────────┘  │  │
│  └──────────────┘     │  ┌─────▼──────┐                │                 │  │
│                       │  │ Connectors │       ┌────────▼─────────────┐   │  │
│                       │  │  Registry  │       │  Repositories (Async)│   │  │
│                       │  └─────┬──────┘       └────────┬─────────────┘   │  │
│                       └────────┼───────────────────────┼─────────────────┘  │
│                                │                       │                    │
│  ┌─────────────────────────────▼───────────────────────▼──────────────────┐ │
│  │                     Intelligence & Pipeline                            │ │
│  │                                                                        │ │
│  │ Normalizer → Deduplicator → CompanyResolver → EmbeddingGenerator       │ │
│  │ RankerStage → PersistenceStage                                         │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                │                                            │
│  ┌─────────────────────────────▼──────────────────────────────────────────┐ │
│  │                         AI Layer                                       │ │
│  │                                                                        │ │
│  │ Providers: Anthropic Claude 3.5 / OpenAI GPT-4o / Ollama               │ │
│  │ Engines: ResumeTailor | CoverLetter | Reviewer | InterviewPrep         │ │
│  │          SkillGap | CareerAdvisor                                      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                │                                            │
│  ┌─────────────────────────────▼──────────────────────────────────────────┐ │
│  │                       Database Layer                                   │ │
│  │                                                                        │ │
│  │ PostgreSQL 15 + pgvector (18 Relational & Vector Tables)               │ │
│  │ Jobs, Companies, Applications, Resumes, Cover Letters, Embeddings      │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Progress Matrix & Phase Blueprint

### Phase 1: Foundational Architecture & Core Contracts ✅ COMPLETED
- **Universal Models**: Implemented Pydantic v2 domain schemas (`Job`, `Company`, `Application`, `User`).
- **Interfaces & Protocols**: Standardized `BaseConnector`, `BasePipelineStage`, `BaseAIEngine`, `BaseEventHandler`, and Repository Protocols.
- **Event Bus System**: Built 12 strongly-typed domain events with strict `correlation_id` propagation for distributed tracing.
- **Database Schema**: Authored `database/schema.sql` defining 18 PostgreSQL tables with `pgvector` HNSW indexes.
- **Pipeline Architecture**: Defined 6-stage sequential ingestion pipeline with standard stage contracts.
- **Connector Framework**: Built `ConnectorRegistry` and `ConnectorRunner` supporting circuit breakers, retries, and telemetry logging.
- **Test Matrix**: Passed unit and integration suites (36 tests passing).

---

### Phase 2: Persistence Layer & Backend API ⚙️ CURRENT IN PROGRESS
- [x] **Repository Interfaces**: Defined async repository contracts in `core/interfaces/repository.py`.
- [x] **Pipeline Stages**: Implemented `NormalizerStage`, `DeduplicatorStage`, `CompanyResolverStage`, and `PersistenceStage`.
- [ ] **SQLAlchemy ORM Models**: Map 18 relational tables to `DeclarativeBase` ORM entities in `database/models/`.
- [ ] **Alembic Migrations**: Configure `alembic/` for automatic schema migrations and revision histories.
- [ ] **Concrete Repositories**: Implement `JobRepository`, `CompanyRepository`, `ApplicationRepository`, and `UserRepository` using SQLAlchemy AsyncSession.
- [ ] **Service Layer**: Implement `JobService`, `CompanyService`, `ApplicationService`, and `ResumeService`.
- [ ] **FastAPI Endpoints**: Build REST API routes (`/api/v1/jobs`, `/api/v1/applications`, `/api/v1/companies`, `/api/v1/health`).

---

### Phase 3 & 4: Production Connector Suite & Asynchronous Queue 🔮 PLANNED
- [ ] **Connector Implementations**:
  - `GreenhouseConnector` (Public REST JSON API)
  - `LeverConnector` (Lever Postings API)
  - `LinkedInConnector`, `JobnetConnector`, `JobbankConnector`, `JobindexConnector`
- [ ] **Resilient Queue Broker**: Integrate Redis + RQ / Arq for async worker job scheduling.
- [ ] **Dead Letter Queue (DLQ)**: Routing failed payloads to `connector_errors` for inspection and automatic retry policies.
- [ ] **Connector Health Metrics**: Dashboard telemetry for success rates, execution latencies, and error rates.

---

### Phase 5 & 6: Embedding Generation, Vector Search & AI Job Ranking 🔮 PLANNED
- [ ] **Embedding Pipeline**: Generate 1536-dim vector embeddings for jobs, companies, and candidate profiles via OpenAI / HuggingFace.
- [ ] **pgvector Similarity Search**: HNSW cosine distance indexing for sub-second vector search.
- [ ] **RankerStage Implementation**: Scoring algorithm evaluating technical skill overlap, domain relevance, experience alignment, and behavioral fit.
- [ ] **Smart Deduplication**: Cross-portal fuzzy title + company + location deduplication.

---

### Phase 7: Generative AI Application Suite 🔮 PLANNED
- [ ] **Resume Engine**: Tailor LaTeX ModernCV templates based on job requirements and verified candidate profiles.
- [ ] **Cover Letter Engine**: Custom LaTeX `cover.cls` generation tailored to target company mission and role.
- [ ] **Reviewer Engine**: Dual-agent critique loop evaluating output accuracy, page length constraints, and alignment.
- [ ] **Interview Prep Simulator**: Interactive role-play simulator generating STAR-method talking points and interviewer questions.
- [ ] **Skill Gap Analysis**: Automated gap detection producing personalized upskilling roadmaps.

---

### Phase 8 & 9: Modern Web Dashboard, CRM & Automation Extensions 🔮 PLANNED
- [ ] **Frontend Application (Next.js App Router)**:
  - **Kanban Board**: Drag-and-drop job application CRM (Wishlist -> Applied -> Interview -> Offer -> Rejected).
  - **Jobs Explorer**: Dynamic search, filtering, and fit score visualization.
  - **Live Resume Studio**: Side-by-side LaTeX code editor and PDF renderer.
- [ ] **Background Automation**:
  - APScheduler cron daemon for automated 6-hour job portal polling.
  - SMTP Email notifications & Webhook alerts for top-scoring job matches.
  - Chrome Extension for one-click job scraping from any web page.

---

## Verification & Testing Strategy

### Automated Verification
1. **Unit & Integration Suite**:
   ```bash
   pytest
   ```
2. **Type Checking & Code Quality**:
   ```bash
   mypy core backend intelligence ai database workers
   ruff check .
   ```
3. **Database Migration Verification**:
   ```bash
   alembic upgrade head
   ```

### Manual Verification
- Deploy git updates to `https://github.com/vinaykhosya/helios`.
- Swagger UI API validation at `http://localhost:8000/docs`.
