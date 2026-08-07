# Helios Engineering & Contribution Guidelines

This document outlines the architectural guidelines and contribution rules for the Helios platform. Every pull request must satisfy these rules before it can be merged.

---

## 1. Architectural Integrity

Stable interfaces and contracts are the key long-term advantage of the Helios platform. We enforce strict layer decoupling.

### Rule 1: Every new feature must satisfy three requirements before it is merged:
1. **Dependency Conformance**: It implements or utilizes an existing contract defined in `core/` (interfaces, models, events, repository protocols) rather than creating a new circular dependency path.
2. **Test Coverage**: It includes unit or integration tests covering the new behavior it introduces.
3. **Contract Stability**: It does not require changing Phase 1 contracts unless the architectural modification has been explicitly approved and documented in a new **Architecture Decision Record (ADR)**.

---

## 2. Decoupling Rules & Import flow

Imports must flow downward. Core must never import infrastructure libraries or other layers.

```
[API / FastAPI Routes] (backend/src/api/)
       ↓
[Services] (backend/src/services/)
       ↓
[Pipeline Stages / Repositories]
       ↓
[Connector Contracts / Interfaces / Core Models] (core/)
```

- **Core models & interfaces** (`core/`) must never import from `backend/`, `ai/`, or `intelligence/`.
- **Services** must only depend on repository interfaces / protocols (defined in `core/interfaces/repository.py`), not concrete SQLAlchemy repositories.
- **FastAPI routes** must only invoke service layers, never call database/repositories directly.
- **AI Engines** (`ai/`) are provider-agnostic. The provider (`BaseProvider` interface) is injected into engines at constructor time.

---

## 3. Telemetry and Observability

All operational services, connectors, and background workers must emit telemetry through our structured logger, tracer, and metrics collector defined in `shared/telemetry/`.

Ensure you:
- Propagate the incoming `correlation_id` when firing events or logging spans.
- Track LLM prompt/completion tokens and costs via `MetricsCollector.record_ai_cost()`.
- Record pipeline stage entry, exit, and drop statistics.

---

## 4. Test Categories

We maintain a strict three-tier testing strategy:

1. **Unit Tests** (`tests/unit/`): No database, no network, no file I/O. Use mock connectors/providers where necessary.
2. **Integration Tests** (`tests/integration/`): Live Postgres/Redis test containers, but external HTTP is mocked or recorded using VCR cassettes (`pytest-recording`).
3. **End-to-End Tests** (`tests/e2e/`): Test full flows, e.g. ingestion run → DB write → ranking scoring → notifications.
