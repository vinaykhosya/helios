<p align="center">
  <img src="claude_animation.gif" alt="Helios" width="200">
</p>

# Helios

**AI Career Intelligence Platform**

Helios is an end-to-end career intelligence system. It ingests job postings from multiple portals, ranks them against your profile using vector embeddings and AI, and provides a full application workflow: tailored resume generation, cover letter writing, interview preparation, and application tracking.

---

## What Helios Is

| Capability | Status |
|-----------|--------|
| Multi-portal job ingestion | Phase 3 |
| AI-powered job ranking | Phase 4 |
| Resume generation (LaTeX, tailored) | Phase 2 |
| Cover letter generation | Phase 2 |
| Interview preparation | Phase 2 |
| Application CRM (kanban) | Phase 5 |
| Skill gap analysis + learning plan | Phase 4 |
| Career path recommendations | Phase 4 |
| Dashboard + analytics | Phase 5 |
| Email / push notifications | Phase 6 |

---

## Architecture

Helios is organized as a layered monorepo:

```
helios/
├── core/           ← Universal contracts (models, interfaces, events)
├── backend/        ← FastAPI application + connectors + services
├── ai/             ← LLM providers + AI engines
├── intelligence/   ← Ranking, embeddings, deduplication, recommendations
├── database/       ← PostgreSQL schema (18 tables, pgvector)
├── workers/        ← Event-driven background workers
├── docs/           ← Architecture + ADRs
└── (existing ai-job-search engine files, untouched)
```

The existing `ai-job-search` repository is the **engine layer**. Resume generation, cover letter writing, interview preparation, and application review from that repository are extracted into `ai/engines/` in Phase 2.

See [`docs/architecture.md`](docs/architecture.md) for the full system overview.

---

## Phase 1: Foundational Contracts (Current)

Phase 1 establishes the architecture without building any runtime. Every file either defines a contract or documents a decision.

**Delivered:**
- [Universal Job Model](core/models/job.py) — Pydantic v2, 22 fields
- [Company Model](core/models/company.py)
- [Application Model](core/models/application.py)
- [User Model](core/models/user.py)
- [BaseConnector interface](core/interfaces/connector.py)
- [BasePipelineStage interface](core/interfaces/pipeline_stage.py)
- [BaseAIEngine + BaseProvider interfaces](core/interfaces/ai_engine.py)
- [BaseEventHandler interface](core/interfaces/event_handler.py)
- [Event contracts](core/events/definitions.py) — 12 typed events
- [Domain exceptions](core/exceptions.py)
- [ConnectorRegistry](backend/src/connectors/registry.py)
- [Ingestion pipeline stage contracts](intelligence/pipeline/stages.py)
- [Database schema](database/schema.sql) — 18 tables, pgvector embeddings
- [Architecture docs](docs/architecture.md), [Pipeline docs](docs/pipeline.md), [Data schemas](docs/data-schemas.md)
- [ADR-001](docs/adr/ADR-001-monorepo-phase-structure.md) through [ADR-006](docs/adr/ADR-006-ingestion-pipeline.md)

---

## Using the Existing Job Search Engine

The original `ai-job-search` engine is fully functional and untouched. Run it with Claude Code:

```bash
claude
/setup    # populate your candidate profile
/scrape   # find new job matches
/apply <url>   # evaluate, draft CV + cover letter, review
/upskill  # skill gap analysis
```

See [`SETUP.md`](SETUP.md) for the full setup guide.

---

## Roadmap

| Phase | Scope |
|-------|-------|
| **1** | ✅ Architecture · Models · Interfaces · Events · DB Schema |
| 2 | FastAPI · SQLAlchemy · Alembic · Redis · Auth |
| 3 | Connector implementations · Ingestion pipeline (Stages 1–3) |
| 4 | Embeddings · pgvector · Ranking · Deduplication (Stage 4–5) |
| 5 | Frontend: Dashboard · Jobs · CRM · Resume Builder |
| 6 | Automation: Scheduler · Email · Push · Browser Extension |

---

## License

MIT
