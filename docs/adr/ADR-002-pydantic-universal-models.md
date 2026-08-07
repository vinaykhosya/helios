# ADR-002: Pydantic v2 as the Universal Model Layer

**Date:** 2026-07-06
**Status:** Accepted
**Deciders:** Platform Architecture

---

## Context

The Helios platform requires a universal `Job` model shared across connectors, the ingestion pipeline, AI engines, the backend API, and the database. The model must handle:

- Validation (field types, enums, required vs. optional)
- Serialization to JSON for API responses
- Deserialization from connector payloads
- OpenAPI schema generation for the FastAPI backend
- Partial construction (connectors provide incomplete data — model must tolerate missing fields)

Two candidates were considered:
1. Python `dataclasses` (stdlib)
2. Pydantic v2 `BaseModel`

---

## Decision

**Use Pydantic v2 `BaseModel` for all universal models.**

```python
# Rejected
@dataclass
class Job:
    title: str
    ...

# Accepted
class Job(BaseModel):
    title: str
    ...
```

---

## Rationale

**Validation is built in:**
Pydantic validates on instantiation. A connector returning `deadline: "not-a-date"` raises a clear `ValidationError` rather than silently propagating a bad string.

**FastAPI integration is native:**
FastAPI uses Pydantic models for request/response serialization and OpenAPI schema generation. Using dataclasses would require a conversion layer at every API boundary:
```python
# What we avoid:
dataclass_instance → dict → json → pydantic_model → API response
```

**Serialization is zero-cost:**
`job.model_dump()`, `job.model_dump_json()`, and `Job.model_validate(raw_dict)` replace hand-written serializers.

**Partial construction is straightforward:**
Fields with `Optional[T] = None` or `list[T] = Field(default_factory=list)` handle connectors that cannot populate every field, without special-casing in the connector.

**Schema generation:**
`Job.model_json_schema()` produces a complete JSON Schema for documentation and validation tooling.

---

## Consequences

- ✅ One model definition serves validation, serialization, API responses, and documentation.
- ✅ Type safety enforced at runtime, not just at type-check time.
- ✅ FastAPI integration requires zero boilerplate.
- ⚠️ Pydantic v2 models are not directly JSON-serializable by `json.dumps()` — always use `model.model_dump_json()` or `jsonable_encoder()` from FastAPI.
- ⚠️ SQLAlchemy ORM models in `database/models/` are *not* Pydantic models. The repository layer handles the conversion between ORM rows and Pydantic models (Phase 2).
