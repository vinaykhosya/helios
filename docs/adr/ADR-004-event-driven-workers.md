# ADR-004: Event-Driven Workers Instead of Cron/Polling

**Date:** 2026-07-06
**Status:** Accepted
**Deciders:** Platform Architecture

---

## Context

Helios needs background processing for:
- Running connectors on a schedule
- Generating embeddings for new jobs
- Ranking jobs against user profiles
- Sending notifications when high-fit jobs appear

The two primary patterns for orchestrating this work are:

1. **Cron/polling workers:** Each worker runs on a timer and checks for work.
2. **Event-driven workers:** Workers subscribe to events and react when work arrives.

---

## Decision

**Use event-driven workers. Workers subscribe to events and react asynchronously.**

```
ConnectorWorker (scheduled trigger)
  → ConnectorRunCompleted event
    → IngestionWorker (processes new jobs through pipeline)
      → JobDiscovered event (per new job)
        → EmbeddingWorker (generates vectors)
          → EmbeddingGenerated event
            → RankingWorker (scores job against users)
              → JobRanked event
                → NotificationWorker (sends alert if score ≥ threshold)
```

---

## Rationale

**Loose coupling:**
Workers do not call each other. The `ConnectorWorker` does not know that `EmbeddingWorker` exists. Adding a new subscriber to `JobDiscovered` (e.g., an analytics worker) requires no changes to existing code.

**Scalability:**
High-volume events (e.g., 10,000 `JobDiscovered` events after a large ingestion run) can be processed in parallel by multiple `EmbeddingWorker` instances without changing the architecture.

**Observability:**
Every event is a record. The event log is also an audit trail. Debugging a missing notification means tracing the event chain, not correlating cron log files.

**Idempotency:**
Events enable at-least-once delivery. Workers are designed to be idempotent — processing the same `JobDiscovered` event twice produces no side effects beyond the first.

**Cron survives as a trigger, not an orchestrator:**
The `ConnectorWorker` is still triggered by a cron schedule (`INGESTION_CRON` in `.env`). But it only fires `ConnectorRunStarted/Completed` events — it does not call downstream workers directly.

---

## Phase 2 Implementation

Redis Streams is the recommended backing for Phase 2:
- Persistent (messages survive worker restarts)
- Consumer groups (multiple worker instances share the load)
- Built-in retry on failure
- No separate message broker required (Redis is already a dependency)

---

## Event Contracts (Phase 1)

All events are defined in `core/events/definitions.py`. No event bus implementation exists in Phase 1 — only the Pydantic contracts.

---

## Consequences

- ✅ Workers are loosely coupled and independently scalable.
- ✅ Adding new reactive behaviors requires only a new event handler.
- ✅ Event log provides a natural audit trail.
- ⚠️ Debugging requires distributed tracing (event correlation IDs) — `event_id` fields on all events support this.
- ⚠️ Phase 2 must implement the event bus before any worker-to-worker communication is possible.
