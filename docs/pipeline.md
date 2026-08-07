# Ingestion Pipeline

## Overview

Every job that enters Helios passes through a six-stage ingestion pipeline. The pipeline transforms raw connector output into stored, deduplicated, embedded, and ranked job records.

The pipeline is defined in `intelligence/pipeline/stages.py`.

---

## Pipeline Stages

```
Connector.search() / Connector.fetch()
  ↓ list[Job]  (raw, from portal)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[1] NormalizerStage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓ list[Job]  (clean, typed, validated)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2] DeduplicatorStage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓ list[Job]  (novel jobs only)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[3] CompanyResolverStage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓ list[Job]  (company_id set)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[4] EmbeddingGeneratorStage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓ list[Job]  (embedding_id set)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[5] RankerStage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓ list[Job]  (fit_score set per user)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[6] PersistenceStage
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ↓ Events: JobDiscovered | JobUpdated | NotificationRequested
```

---

## Stage Reference

### Stage 1: NormalizerStage

**Phase:** 3
**Purpose:** Clean and validate raw Job objects from connectors.

| Input | Output | May Drop? |
|-------|--------|-----------|
| Raw Job from connector | Clean Job | Yes — if required fields missing |

**Operations:**
- Strip HTML tags from `description`
- Normalize `title` casing and punctuation (trim, fix ALL-CAPS, etc.)
- Coerce `posted_date` and `deadline` to UTC datetime
- Validate that `title`, `company`, and `source_url` are non-empty
- Drop jobs that cannot be minimally normalized (log reason)

**Does NOT:** Fetch additional data. Pure in-memory transformation.

---

### Stage 2: DeduplicatorStage

**Phase:** 3 (exact), 4 (fuzzy)
**Purpose:** Remove jobs already stored in the database.

| Input | Output | May Drop? |
|-------|--------|-----------|
| Clean Job | Novel Job | Yes — known jobs are dropped |

**Strategy 1 (Phase 3) — Exact match:**
```sql
SELECT id FROM jobs WHERE source = $1 AND source_id = $2
```
Fast, indexed. Handles portals that maintain stable job IDs.

**Strategy 2 (Phase 4) — Fuzzy match:**
Catch reposts where the portal assigns a new ID:
```
normalize(title) = normalize(existing.title)
AND normalize(company) = normalize(existing.company)
AND posted_date BETWEEN existing.posted_date - 7 days AND NOW()
```

If a match is found on either strategy:
- The job is dropped from the pipeline.
- If `deadline` or `is_active` changed, update the existing record.

---

### Stage 3: CompanyResolverStage

**Phase:** 3
**Purpose:** Link each job to a Company record.

| Input | Output | May Drop? |
|-------|--------|-----------|
| Job (company_id = null) | Job (company_id set) | No |

**Process:**
1. Normalize company name: strip `A/S`, `ApS`, `GmbH`, `Inc.`, `Ltd.`, `LLC`, `S.A.`, etc.
2. Lookup by `name_normalized` in the `companies` table.
3. If found: set `job.company_id`.
4. If not found: create new `Company` record with available data (name, website from job). Queue async enrichment.

**Enrichment (async, Phase 3+):** Clearbit, LinkedIn data for logo, size, description.

---

### Stage 4: EmbeddingGeneratorStage

**Phase:** 4
**Purpose:** Generate and store vector embeddings for each job.

| Input | Output | May Drop? |
|-------|--------|-----------|
| Job (embedding_id = null) | Job (embedding_id set) | No (skips on provider failure) |

**Embedding input text:**
```python
f"{job.title}. {job.description[:2000] or ''}. Skills: {', '.join(job.skills)}"
```

**Process:**
1. Call `EmbeddingProvider.embed(text)` → `list[float]` (dimension: 1536)
2. Store in `job_embeddings` table with `model` name.
3. Set `job.embedding_id`.

**On provider failure:** Log error, set `embedding_id = null`, continue pipeline. Jobs without embeddings cannot be ranked by vector similarity but are still stored.

---

### Stage 5: RankerStage

**Phase:** 4
**Purpose:** Score each job against all active user profiles.

| Input | Output | May Drop? |
|-------|--------|-----------|
| Job (embedding_id set) | Job (fit_score set) | No |

**Scoring formula:**

```
base_score   = cosine_similarity(job_embedding, user_embedding)

boost = 0.0
if job.city in user.target_locations:      boost += 0.10
if job.remote == user.preferred_remote:    boost += 0.05
if seniority_match(job, user):             boost += 0.05

fit_score = min(1.0, base_score + boost)
```

**LLM re-ranking (Phase 4+):** Applied to top 20 candidates per user per run. Expensive — uses a fast model (claude-haiku or gpt-4o-mini).

**Output:** `fit_score` is stored in a `user_job_scores` join table (Phase 2 schema addition). The `Job.fit_score` field carries the score for the current user context.

---

### Stage 6: PersistenceStage

**Phase:** 2 (first implementation)
**Purpose:** Write everything to the database and fire events.

| Input | Output |
|-------|--------|
| Enriched Job | Events |

**For each job:**
1. `UPSERT` the `jobs` record (`ON CONFLICT (source, source_id) DO UPDATE`).
2. If `embedding_id` is set: ensure `job_embeddings` record exists.
3. If `fit_score` is set: write to `user_job_scores` join table.
4. Fire `JobDiscovered` if the job is new.
5. Fire `JobUpdated` if existing fields changed.
6. Fire `NotificationRequested` if `fit_score >= user.settings.new_match_threshold`.

**This is the only stage that writes to the database.**

---

## Observability

Each stage logs on entry and exit:

```
[normalizer]    300 in → 298 out (2 dropped: missing title)
[deduplicator]  298 in → 148 out (150 dropped: already known)
[company_resolver] 148 in → 148 out (12 created, 136 matched)
[embedding_gen] 148 in → 146 out (2 skipped: provider error)
[ranker]        146 in → 146 out (fit_scores: min=0.12 max=0.91)
[persistence]   146 in → 146 stored (events: 146 JobDiscovered, 8 NotificationRequested)
```

---

## Failure Modes

| Failure | Stage | Behavior |
|---------|-------|----------|
| Connector returns 429 | Pre-pipeline | Retry with backoff; abort run after max retries |
| Job missing required fields | NormalizerStage | Drop job, log warning |
| DB unreachable (dedup lookup) | DeduplicatorStage | Abort entire pipeline, fire `ConnectorRunFailed` |
| Embedding provider down | EmbeddingGeneratorStage | Skip embedding, continue; job stored without embedding |
| DB unreachable (write) | PersistenceStage | Abort, fire `ConnectorRunFailed` |

---

## Adding a New Stage

1. Create a class in `intelligence/pipeline/stages.py` that extends `BasePipelineStage`.
2. Implement `process(jobs: list[Job]) -> list[Job]`.
3. Add it to `INGESTION_PIPELINE` list at the appropriate position.
4. Write an ADR if the new stage changes pipeline order.
5. Add unit tests: pass synthetic jobs, assert on output.
