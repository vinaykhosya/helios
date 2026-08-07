# ADR-001: Monorepo Phase Structure

**Date:** 2026-07-06
**Status:** Accepted
**Deciders:** Platform Architecture

---

## Context

Helios is an AI Career Intelligence Platform being built incrementally from an existing `ai-job-search` repository. The team must decide how to organize code across multiple concerns: the existing Claude Code engine, a new Python backend, a Next.js frontend, job portal connectors, AI engines, database access, and background workers.

The two primary options were:

1. **Polyrepo**: One Git repository per service (backend, frontend, connectors, workers).
2. **Monorepo**: All code in one Git repository, organized by `backend/`, `frontend/`, `core/`, etc.

---

## Decision

**Use a monorepo with a phased build-out.**

All Helios code lives in one repository. Phases define *what gets built* — not where code lives.

```
helios/
├── core/           ← universal contracts (all phases depend on this)
├── backend/        ← Phase 2+
├── frontend/       ← Phase 5+
├── intelligence/   ← Phase 4+
├── ai/             ← Phase 2+
├── database/       ← Phase 1 (schema), Phase 2 (ORM)
├── workers/        ← Phase 3+
├── docs/
└── (existing repo files, untouched)
```

---

## Rationale

**Why monorepo:**
- The universal `Job` model in `core/` is imported by `backend/`, `intelligence/`, `workers/`, and `ai/` simultaneously. A polyrepo would require publishing `core/` as a versioned package before any other repo could import it — significant overhead during early development.
- Schema changes, model changes, and interface changes affect multiple layers atomically. A monorepo makes these cross-cutting changes in a single commit.
- The existing `ai-job-search` files (`.claude/`, `.agents/`) need to coexist with Helios without disruption. A monorepo allows this with no file moves.

**Why not microservices yet:**
- Microservices are a deployment strategy, not an architecture strategy. The internal module boundaries (`core/`, `backend/`, `intelligence/`) enforce separation of concerns without the operational overhead of separate deployments.
- Phase 6 can extract high-traffic services (e.g., the ingestion worker) into separate deployments without changing the code structure.

---

## Consequences

- ✅ Single import namespace for `core.models`, `core.interfaces`, `core.events`.
- ✅ Cross-cutting changes are atomic commits.
- ✅ Existing `ai-job-search` files are untouched in the same repo.
- ⚠️ As the repo grows, the CI pipeline must scope tests by subdirectory to remain fast.
- ⚠️ The `core/` package must remain free of heavy runtime dependencies (no FastAPI, no DB drivers). It is consumed by all other packages.
