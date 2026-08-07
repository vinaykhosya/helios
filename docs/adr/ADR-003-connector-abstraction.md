# ADR-003: Connectors Are Backend Infrastructure, Not a Top-Level Package

**Date:** 2026-07-06
**Status:** Accepted
**Deciders:** Platform Architecture

---

## Context

Helios integrates with multiple job portals (Jobindex, Jobbank, LinkedIn, Greenhouse, Lever, etc.) via connector classes. The question was where to place these connectors in the monorepo.

**Option A:** Top-level `connectors/` package at the repository root.
**Option B:** `backend/src/connectors/` — connectors are backend infrastructure.

---

## Decision

**Connectors live at `backend/src/connectors/`.**

The `BaseConnector` interface contract lives at `core/interfaces/connector.py` (shared, no runtime deps). Concrete implementations live at `backend/src/connectors/`.

---

## Rationale

**Connectors are backend infrastructure, not standalone services:**

```
frontend/           ← never calls connectors
core/               ← defines BaseConnector (interface only)
backend/src/
  connectors/       ← concrete implementations (jobindex.py, greenhouse.py, …)
  services/         ← call connectors to fetch jobs
workers/            ← call connectors via services for ingestion runs
```

The frontend never calls connectors. Workers and services do. Both `workers/` and `backend/src/services/` are backend concerns. Placing connectors in `backend/src/connectors/` reflects this dependency graph accurately.

**A top-level `connectors/` would imply independence it doesn't have:**
If connectors were top-level, they would appear to be an independently deployable component. They are not — they require the same runtime environment as the backend (httpx, event bus, error reporting) and share the backend's configuration (API keys, proxy settings, rate limit state).

**The interface contract remains in `core/`:**
The `BaseConnector` ABC in `core/interfaces/connector.py` has no runtime dependencies and is importable everywhere. This allows `intelligence/` and `workers/` to depend on the interface without depending on the backend package.

---

## Existing CLI Tools

The existing TypeScript/Bun CLI tools in `.agents/skills/*/cli/` are **not** replaced in Phase 1 or Phase 3. They continue to function as Claude Code tools. Phase 3 connector implementations are new Python classes that call the same portals via their APIs — they do not wrap the TypeScript CLIs.

---

## Phase 3 Connector Structure

```
backend/src/connectors/
├── __init__.py
├── registry.py          ← ConnectorRegistry (Phase 1 contract)
├── jobindex.py          ← JobindexConnector(BaseConnector)
├── jobbank.py           ← JobbankConnector(BaseConnector)
├── jobdanmark.py        ← JobdanmarkConnector(BaseConnector)
├── jobnet.py            ← JobnetConnector(BaseConnector)
├── linkedin.py          ← LinkedInConnector(BaseConnector)
├── greenhouse.py        ← GreenhouseConnector(BaseConnector)
└── lever.py             ← LeverConnector(BaseConnector)
```

---

## Consequences

- ✅ Dependency graph is clean: frontend → backend → connectors (never reverse).
- ✅ Connector implementations share the backend's runtime, config, and HTTP client.
- ✅ Adding a new connector requires only: one new file + `@ConnectorRegistry.register`.
- ⚠️ Workers that call connectors must import from `backend.src.connectors`, creating a dependency on `backend`. If workers are ever extracted to a separate deployment, this import path must be resolved.
