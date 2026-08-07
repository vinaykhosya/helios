# ADR-005: Intelligence Layer Is Separate from AI Layer

**Date:** 2026-07-06
**Status:** Accepted
**Deciders:** Platform Architecture

---

## Context

Helios needs job ranking, deduplication, recommendation, and analytics. The question was whether these belong in the `ai/` package alongside the LLM-powered engines (resume generation, cover letter, etc.).

---

## Decision

**Ranking, deduplication, recommendation, and analytics live in `intelligence/`, not `ai/`.**

```
ai/
  providers/    ← LLM infrastructure (OpenAI, Anthropic, Ollama)
  engines/      ← LLM business logic (Resume, CoverLetter, Reviewer, Interview, SkillGap)
  prompts/      ← Prompt templates
  memory/       ← Conversation / session memory

intelligence/
  pipeline/     ← Ingestion pipeline stages
  ranking/      ← Job fit scoring (vectors + rules + optional LLM)
  deduplication/← Duplicate job detection (exact match + fuzzy)
  recommendation/← Career path and role recommendations
  analytics/    ← Skill gap, market trends, funnel analysis
```

---

## Rationale

**Ranking is not purely AI:**

Job ranking in Helios combines:
1. **Vector similarity** (cosine distance between job embedding and user embedding) — math, not AI
2. **Rule-based boosts** (location match, remote preference, seniority alignment) — deterministic logic
3. **LLM re-ranking** (optional, expensive, applied only to top N candidates) — AI

If ranking lived in `ai/`, it would conflate infrastructure (LLM API calls) with business logic (scoring rules) with data operations (vector lookups). Keeping it in `intelligence/` makes the boundary clear: `intelligence/` uses `ai/` as one component among several, not as its identity.

**Deduplication is not AI at all:**
Exact match deduplication `(source, source_id)` is a database lookup. Fuzzy deduplication (title + company within a time window) is string similarity + database. Neither requires an LLM.

**`ai/` should contain only LLM-dependent logic:**
An `ai/` module that contains vector math, SQL queries, and cron schedules becomes a grab-bag. By restricting `ai/` to *things that call an LLM provider*, its scope stays clear.

---

## Dependency Graph

```
intelligence/ranking/  → ai/providers/ (for LLM re-ranking, optional)
intelligence/ranking/  → database/     (for vector similarity)
intelligence/ranking/  → core/models/  (for Job, User)

ai/engines/resume/     → ai/providers/ (always, for generation)
ai/engines/resume/     → core/models/  (for Job, User)
ai/engines/resume/     → ai/prompts/   (for prompt templates)

# intelligence/ depends on ai/ optionally
# ai/ never depends on intelligence/
```

---

## Consequences

- ✅ `ai/` scope is clear: it contains only LLM provider calls and LLM business logic.
- ✅ `intelligence/` can add new algorithms (e.g., a collaborative filtering recommender) without touching the AI layer.
- ✅ The ranking system can be tested deterministically without mocking LLM providers.
- ⚠️ When ranking does use LLM re-ranking, the import from `intelligence/` into `ai/` must flow through `core/interfaces/`, not directly.
