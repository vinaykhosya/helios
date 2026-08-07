# Helios Architecture

## Overview

Helios is an AI Career Intelligence Platform. It ingests job postings from multiple portals, ranks them against user profiles, and provides AI-powered application tooling (resume generation, cover letters, interview preparation, skill gap analysis).

The existing [`ai-job-search`](https://github.com/MadsLorentzen/ai-job-search) repository provides four reusable AI engines (resume, cover letter, interview, reviewer) that are extracted into the `ai/engines/` layer.

---

## System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                          HELIOS PLATFORM                            │
│                                                                     │
│  ┌─────────────┐    ┌──────────────────────────────────────────┐   │
│  │  Frontend   │    │               Backend                    │   │
│  │  (Phase 5)  │◄──►│  ┌──────────┐  ┌────────────────────┐  │   │
│  │             │    │  │   API    │  │    Services        │  │   │
│  │  /dashboard │    │  │  Routes  │  │  JobService        │  │   │
│  │  /jobs      │    │  │          │  │  ApplicationService │  │   │
│  │  /apply     │    │  └────┬─────┘  │  ResumeService     │  │   │
│  │  /analytics │    │       │        │  CompanyService     │  │   │
│  └─────────────┘    │  ┌────▼─────┐  └────────┬───────────┘  │   │
│                     │  │Connectors│            │              │   │
│                     │  │ Registry │            │              │   │
│                     │  └────┬─────┘  ┌─────────▼──────────┐  │   │
│                     │       │        │   Repositories     │  │   │
│                     └───────┼────────┴─────────┬──────────┘──┘   │
│                             │                  │                   │
│  ┌──────────────────────────▼──────────────────▼────────────────┐ │
│  │                    Intelligence                               │ │
│  │                                                               │ │
│  │  Connector → Normalizer → Deduplicator → CompanyResolver      │ │
│  │           → EmbeddingGenerator → Ranker → Persistence         │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐ │
│  │                         AI Layer                              │ │
│  │                                                               │ │
│  │  Providers: Anthropic | OpenAI | Ollama                       │ │
│  │  Engines: Resume | CoverLetter | Reviewer | Interview |       │ │
│  │           SkillGap | CareerAdvisor                            │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                             │                                       │
│  ┌──────────────────────────▼────────────────────────────────────┐ │
│  │                       Database                                │ │
│  │                                                               │ │
│  │  PostgreSQL 15 + pgvector                                     │ │
│  │  18 tables: jobs, companies, applications, users,             │ │
│  │  resumes, cover_letters, interview_sessions, saved_jobs,      │ │
│  │  skill_analytics, notifications, connector_health,            │ │
│  │  connector_runs, connector_errors, job_embeddings,            │ │
│  │  company_embeddings, user_embeddings, audit_logs              │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Contracts

Everything in Helios is built around three foundational contracts defined in `core/`:

### 1. Universal Job Model (`core/models/job.py`)

The central data object. Every connector produces a `Job`. Every service, AI engine, and pipeline stage consumes a `Job`. It is never subclassed per-connector — connectors adapt their data to the model, not the reverse.

Key fields: `source`, `source_id`, `title`, `company`, `location`, `remote`, `employment_type`, `salary`, `skills`, `fit_score`, `embedding_id`.

### 2. BaseConnector (`core/interfaces/connector.py`)

Four-method contract: `search()`, `fetch()`, `normalize()`, `health_check()`. Every job portal integration implements this. Connectors live in `backend/src/connectors/`. The frontend never calls connectors directly.

### 3. Ingestion Pipeline (`intelligence/pipeline/stages.py`)

Six sequential stages that every ingested job passes through. Each stage implements `BasePipelineStage.process(list[Job]) -> list[Job]`. Stages may filter, enrich, or annotate jobs. See `docs/pipeline.md` for full details.

---

## Data Flow: Job Ingestion

```
1. Scheduler triggers ConnectorWorker (cron: every 6h)
2. ConnectorWorker calls ConnectorRegistry.all()
3. For each Connector:
   a. connector.search(query, location) → list[Job]
   b. pipeline.run(jobs):
      - NormalizerStage     → clean and validate
      - DeduplicatorStage   → drop known jobs
      - CompanyResolverStage → link to Company records
      - EmbeddingGenerator  → store vectors
      - RankerStage         → score against user profiles
      - PersistenceStage    → write to DB, fire events
4. JobDiscovered events → EmbeddingWorker, RankingWorker
5. JobRanked events → NotificationWorker (if score ≥ threshold)
6. NotificationRequested → email / in-app notification
```

## Data Flow: Job Application

```
1. User submits job URL or text via frontend or Claude Code /apply
2. ApplicationService.create(user_id, job_id) → Application record
3. ResumeEngine.run(context) → tailored LaTeX CV
4. CoverLetterEngine.run(context) → tailored LaTeX cover letter
5. ReviewerEngine.run(drafts) → critique + revision
6. ApplicationService.update(resume_id, cover_letter_id)
7. ApplicationStatusChanged event → NotificationWorker
```

---

## Package Dependency Rules

```
core/           ← no runtime deps (only pydantic)
  ↑
backend/        ← depends on core + database drivers
ai/             ← depends on core + LLM provider SDKs
intelligence/   ← depends on core + ai/ (optionally)
workers/        ← depends on core + backend + intelligence
frontend/       ← depends on backend API only (HTTP)
```

**Rules:**
- `core/` must never import from `backend/`, `ai/`, or `intelligence/`.
- `ai/` must never import from `backend/` or `intelligence/`.
- `frontend/` must never import Python packages — it communicates via the HTTP API only.

---

## Existing Repository (ai-job-search Engine)

The following files from the original repository are preserved untouched and serve as the source material for Phase 2 AI engine implementations:

| Original File | Helios Engine |
|---------------|---------------|
| `.claude/commands/apply.md` (Steps 2, 4) | `ai/engines/resume/` |
| `.claude/skills/job-application-assistant/06-cover-letter-templates.md` | `ai/engines/cover_letter/` |
| `.claude/commands/apply.md` (Steps 3–4, reviewer) | `ai/engines/reviewer/` |
| `.claude/skills/job-application-assistant/07-interview-prep.md` | `ai/engines/interview/` |
| `.claude/skills/upskill/SKILL.md` | `ai/engines/skill_gap/` |
| `.claude/skills/job-application-assistant/04-job-evaluation.md` | `ai/engines/career_advisor/` |

All `.agents/skills/*/cli/` TypeScript tools remain functional as Claude Code tools and are not replaced until Phase 3 connector implementations cover the same portals.

---

## Phase Roadmap

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Architecture · Models · Interfaces · Events · DB Schema · Docs | ✅ Complete |
| 2 | FastAPI · SQLAlchemy · Alembic · Redis · Auth · PersistenceStage | Planned |
| 3 | Connector implementations · Normalizer · Deduplicator · CompanyResolver | Planned |
| 4 | Embeddings · pgvector · Ranking · Deduplication (fuzzy) | Planned |
| 5 | Frontend: Dashboard · Jobs · Applications · Resume Builder · Analytics | Planned |
| 6 | Automation: Scheduler · Email · Push · Browser Extension | Planned |
