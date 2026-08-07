# ADR-006: Ingestion Pipeline as a First-Class Architecture Pattern

**Date:** 2026-07-06
**Status:** Accepted
**Deciders:** Platform Architecture

---

## Context

The original `ai-job-search` repository ingested jobs by running TypeScript CLI tools and storing results in `job_scraper/seen_jobs.json` (deduplication) and presenting them as a flat list.

Helios needs a richer ingestion model: normalization, deduplication against a real database, company resolution, vector embedding generation, per-user scoring, and persistence. The question was how to structure this multi-step process.

---

## Decision

**Treat job ingestion as an explicit, ordered pipeline of stages.**

```
Connector
  ↓ list[Job] (raw, partial)
[1] NormalizerStage
  ↓ list[Job] (clean, typed)
[2] DeduplicatorStage
  ↓ list[Job] (novel only)
[3] CompanyResolverStage
  ↓ list[Job] (company_id set)
[4] EmbeddingGeneratorStage
  ↓ list[Job] (embedding_id set)
[5] RankerStage
  ↓ list[Job] (fit_score set per user)
[6] PersistenceStage
  ↓ events: JobDiscovered, JobUpdated, NotificationRequested
```

Each stage implements `BasePipelineStage.process(jobs: list[Job]) -> list[Job]`.

---

## Rationale

**Stages are independently testable:**
Each stage receives a `list[Job]` and returns a `list[Job]`. Unit tests can pass synthetic jobs and assert on the output without running the full pipeline.

**Stages can be skipped or reordered per run type:**
A manual "refresh single job" run might skip `DeduplicatorStage` and go directly to `PersistenceStage`. A "re-embed all jobs" maintenance task runs only `EmbeddingGeneratorStage` + `PersistenceStage`. The pipeline is composable.

**Failure isolation:**
If `EmbeddingGeneratorStage` fails (provider down, quota exceeded), the pipeline can fall back to skipping that stage and running `PersistenceStage` without embeddings. Jobs are stored; embeddings are generated later.

**Observability:**
Each stage logs how many jobs entered and exited, with reasons for drops. The pipeline is a linear audit trail: "300 found → 280 normalized → 150 new (130 deduplicated) → 150 company-resolved → 148 embedded → 148 ranked → 148 persisted."

**The existing repo is not a pipeline — it is an ad hoc script:**
The `job-scraper` skill runs WebSearch, loops over results, checks `seen_jobs.json`, and presents a table. This works for a single user running Claude Code interactively. It cannot serve multiple users, operate asynchronously, or scale. The pipeline architecture solves all of this without discarding the underlying scraping logic (which moves into connector implementations).

---

## Stage Implementation Phases

| Stage | Phase | Blocking? |
|-------|-------|-----------|
| NormalizerStage | 3 | No — jobs pass through un-normalized until Phase 3 |
| DeduplicatorStage | 3 (exact) / 4 (fuzzy) | No — all jobs pass through until Phase 3 |
| CompanyResolverStage | 3 | No — company_id remains null until Phase 3 |
| EmbeddingGeneratorStage | 4 | No — embedding_id remains null until Phase 4 |
| RankerStage | 4 | No — fit_score remains null until Phase 4 |
| PersistenceStage | 2 | **Yes** — without this, no jobs are stored |

PersistenceStage is the only Phase 2 blocker. All other stages degrade gracefully.

---

## Consequences

- ✅ Each stage is independently testable, replaceable, and skippable.
- ✅ The pipeline provides natural observability (entry/exit counts per stage).
- ✅ New stages can be inserted without modifying existing ones.
- ⚠️ Pipeline stage order is architecture — reorder only with an ADR update.
- ⚠️ Stages that mutate jobs (embedding_id, fit_score) must return new Job objects or use `model.model_copy(update={...})`, never mutate the input list in place.
