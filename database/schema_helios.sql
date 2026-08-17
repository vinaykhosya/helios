-- ============================================================
-- HELIOS SUPABASE DATABASE SCHEMA v3.0
-- Target: Supabase PostgreSQL (Project ID: tyajlotsxwocxxawcwta)
-- Schema Namespace: helios
-- Extensions: pgcrypto (UUIDs), pgvector (1536-dim embeddings)
-- ============================================================

CREATE SCHEMA IF NOT EXISTS helios;
SET search_path TO helios, public;

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Users ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.users (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT            UNIQUE NOT NULL,
    name                TEXT,
    profile             JSONB,                          -- candidate profile model
    settings            JSONB           DEFAULT '{}',   -- user settings
    target_roles        TEXT[],
    target_locations    TEXT[],
    skills              TEXT[],
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

-- ── Companies ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.companies (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT            NOT NULL,
    name_normalized     TEXT,                           -- lowercase, stripped legal suffixes
    website             TEXT,
    industry            TEXT,
    size                TEXT,                           -- "1-10" | "11-50" | "51-200" etc.
    description         TEXT,
    logo_url            TEXT,
    linkedin_url        TEXT,
    glassdoor_url       TEXT,
    headquarters        TEXT,
    founded_year        INTEGER,
    salary_data         JSONB,                          -- from salary lookup
    tech_stack          TEXT[],
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_name_norm
    ON helios.companies (name_normalized);

-- ── Jobs ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.jobs (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source
    source                  TEXT        NOT NULL,       -- connector name (JobSource enum)
    source_id               TEXT        NOT NULL,       -- portal-native identifier
    source_url              TEXT        NOT NULL,

    -- Content
    title                   TEXT        NOT NULL,
    description             TEXT,
    company_id              UUID        REFERENCES helios.companies(id),
    company_name            TEXT        NOT NULL,       -- denormalized for fast reads

    -- Location
    location                TEXT,                       -- raw string from portal
    city                    TEXT,
    country                 TEXT        DEFAULT 'Denmark',
    remote                  TEXT        DEFAULT 'on_site',
    relocation_supported    BOOLEAN     DEFAULT FALSE,
    visa_sponsorship        BOOLEAN     DEFAULT FALSE,

    -- Role classification
    employment_type         TEXT        DEFAULT 'full_time',
    seniority               TEXT,
    experience_years        INTEGER,
    education_required      TEXT,
    security_clearance      BOOLEAN     DEFAULT FALSE,
    languages_required      TEXT[],

    -- Compensation
    salary_min              INTEGER,
    salary_max              INTEGER,
    salary_currency         TEXT        DEFAULT 'DKK',
    salary_raw              TEXT,
    salary_confidence       TEXT        DEFAULT 'unknown',
    benefits                TEXT[],

    -- Taxonomy
    skills                  TEXT[],
    industry                TEXT,

    -- Timing
    posted_date             TIMESTAMPTZ,
    deadline                TIMESTAMPTZ,
    apply_url               TEXT,
    role_family             TEXT,
    role_relevance          TEXT        DEFAULT 'UNKNOWN',
    role_relevance_confidence NUMERIC(4,2) DEFAULT 0.00,
    adjacent_ml_evidence_score NUMERIC(4,2) DEFAULT 0.00,

    -- Intelligence
    is_active               BOOLEAN     DEFAULT TRUE,
    idempotency_key         TEXT        UNIQUE,

    -- Metadata
    raw_data                JSONB,
    fetched_at              TIMESTAMPTZ DEFAULT NOW(),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_source
    ON helios.jobs (source, source_id);
CREATE INDEX IF NOT EXISTS idx_jobs_company
    ON helios.jobs (company_id);
CREATE INDEX IF NOT EXISTS idx_jobs_posted
    ON helios.jobs (posted_date DESC);

-- ── Applications ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.applications (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES helios.users(id) ON DELETE CASCADE,
    job_id              UUID        REFERENCES helios.jobs(id),
    status              TEXT        NOT NULL DEFAULT 'saved',
    applied_at          TIMESTAMPTZ,
    resume_id           UUID,
    cover_letter_id     UUID,
    fit_rating          NUMERIC(4,2),                   -- 0.00–1.00
    notes               TEXT,
    contact_person      TEXT,
    source_channel      TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_applications_user
    ON helios.applications (user_id);
CREATE INDEX IF NOT EXISTS idx_applications_status
    ON helios.applications (status);
CREATE INDEX IF NOT EXISTS idx_applications_job
    ON helios.applications (job_id);

-- ── Resumes ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.resumes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES helios.users(id) ON DELETE CASCADE,
    job_id          UUID        REFERENCES helios.jobs(id),
    file_path       TEXT,
    latex_source    TEXT,
    version         INTEGER     DEFAULT 1,
    is_master       BOOLEAN     DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Cover Letters ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.cover_letters (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES helios.users(id) ON DELETE CASCADE,
    job_id          UUID        REFERENCES helios.jobs(id),
    file_path       TEXT,
    latex_source    TEXT,
    version         INTEGER     DEFAULT 1,
    language        TEXT        DEFAULT 'en',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Interview Sessions ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.interview_sessions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES helios.users(id) ON DELETE CASCADE,
    application_id  UUID        REFERENCES helios.applications(id),
    stage           TEXT,
    questions       JSONB,
    answers         JSONB,
    talking_points  TEXT,
    scheduled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Saved Jobs ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.saved_jobs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES helios.users(id) ON DELETE CASCADE,
    job_id      UUID        NOT NULL REFERENCES helios.jobs(id) ON DELETE CASCADE,
    fit_score   NUMERIC(4,2),
    notes       TEXT,
    saved_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ── Notifications ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.notifications (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES helios.users(id) ON DELETE CASCADE,
    type        TEXT        NOT NULL,
    title       TEXT        NOT NULL,
    body        TEXT,
    metadata    JSONB       DEFAULT '{}',
    is_read     BOOLEAN     DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Job Embeddings ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.job_embeddings (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      UUID        NOT NULL REFERENCES helios.jobs(id) ON DELETE CASCADE,
    model       TEXT        NOT NULL,
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── Audit Logs ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS helios.audit_logs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        REFERENCES helios.users(id),
    action      TEXT        NOT NULL,
    entity_type TEXT,
    entity_id   UUID,
    before      JSONB,
    after       JSONB,
    ip_address  INET,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

-- Circular FK setup
ALTER TABLE helios.applications
    DROP CONSTRAINT IF EXISTS fk_applications_resume,
    ADD CONSTRAINT fk_applications_resume
    FOREIGN KEY (resume_id) REFERENCES helios.resumes(id);

ALTER TABLE helios.applications
    DROP CONSTRAINT IF EXISTS fk_applications_cover_letter,
    ADD CONSTRAINT fk_applications_cover_letter
    FOREIGN KEY (cover_letter_id) REFERENCES helios.cover_letters(id);
