-- ============================================================
-- HELIOS DATABASE SCHEMA  v1.0
-- Engine: PostgreSQL 15+
-- Extensions: pgcrypto (uuid generation), pgvector (embeddings)
-- ============================================================
-- Tables (18):
--   Users, Companies, Jobs, Applications, Resumes, CoverLetters,
--   InterviewSessions, SavedJobs, SkillAnalytics, Notifications,
--   ConnectorHealth, ConnectorRuns, ConnectorErrors,
--   JobEmbeddings, CompanyEmbeddings, UserEmbeddings, AuditLogs
-- ============================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector: https://github.com/pgvector/pgvector


-- ── Users ──────────────────────────────────────────────────────────────────

CREATE TABLE users (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    email               TEXT            UNIQUE NOT NULL,
    name                TEXT,
    profile             JSONB,                          -- structured candidate profile
    settings            JSONB           DEFAULT '{}',   -- UserSettings fields
    target_roles        TEXT[],
    target_locations    TEXT[],
    skills              TEXT[],
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);


-- ── Companies ──────────────────────────────────────────────────────────────

CREATE TABLE companies (
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
    salary_data         JSONB,                          -- from salary_lookup integration
    tech_stack          TEXT[],
    created_at          TIMESTAMPTZ     DEFAULT NOW(),
    updated_at          TIMESTAMPTZ     DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_companies_name_norm
    ON companies (name_normalized);


-- ── Jobs ───────────────────────────────────────────────────────────────────

CREATE TABLE jobs (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Source
    source                  TEXT        NOT NULL,       -- connector name (JobSource enum)
    source_id               TEXT        NOT NULL,       -- portal-native identifier
    source_url              TEXT        NOT NULL,

    -- Content
    title                   TEXT        NOT NULL,
    description             TEXT,
    company_id              UUID        REFERENCES companies(id),
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

    -- Intelligence
    is_active               BOOLEAN     DEFAULT TRUE,
    idempotency_key         TEXT        UNIQUE,

    -- Metadata
    raw_data                JSONB,
    fetched_at              TIMESTAMPTZ DEFAULT NOW(),
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_jobs_source
    ON jobs (source, source_id);
CREATE INDEX idx_jobs_company
    ON jobs (company_id);
CREATE INDEX idx_jobs_posted
    ON jobs (posted_date DESC);
CREATE INDEX idx_jobs_deadline
    ON jobs (deadline)   WHERE deadline IS NOT NULL;
CREATE INDEX idx_jobs_active
    ON jobs (is_active)  WHERE is_active = TRUE;
CREATE INDEX idx_jobs_skills
    ON jobs USING GIN (skills);
CREATE INDEX idx_jobs_location
    ON jobs (city, country);


-- ── Applications ───────────────────────────────────────────────────────────
-- Replaces job_search_tracker.csv

CREATE TABLE applications (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id              UUID        REFERENCES jobs(id),
    status              TEXT        NOT NULL DEFAULT 'saved',
    applied_at          TIMESTAMPTZ,
    resume_id           UUID,                           -- set after resumes record created
    cover_letter_id     UUID,                           -- set after cover_letters record created
    fit_rating          NUMERIC(4,2),                   -- 0.00–1.00
    notes               TEXT,
    contact_person      TEXT,
    source_channel      TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_applications_user
    ON applications (user_id);
CREATE INDEX idx_applications_status
    ON applications (status);
CREATE INDEX idx_applications_job
    ON applications (job_id);


-- ── Resumes ────────────────────────────────────────────────────────────────

CREATE TABLE resumes (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id          UUID        REFERENCES jobs(id),    -- NULL = master resume
    file_path       TEXT,
    latex_source    TEXT,
    version         INTEGER     DEFAULT 1,
    is_master       BOOLEAN     DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_resumes_user
    ON resumes (user_id);
CREATE INDEX idx_resumes_versions
    ON resumes (user_id, job_id, version DESC);


-- ── Cover Letters ──────────────────────────────────────────────────────────

CREATE TABLE cover_letters (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id          UUID        REFERENCES jobs(id),
    file_path       TEXT,
    latex_source    TEXT,
    version         INTEGER     DEFAULT 1,
    language        TEXT        DEFAULT 'en',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_cover_letters_user
    ON cover_letters (user_id);


-- ── Interview Sessions ─────────────────────────────────────────────────────

CREATE TABLE interview_sessions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id  UUID        REFERENCES applications(id),
    stage           TEXT,                               -- phone | technical | case | final
    questions       JSONB,
    answers         JSONB,
    talking_points  TEXT,
    scheduled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_interview_sessions_user
    ON interview_sessions (user_id);
CREATE INDEX idx_interview_sessions_app
    ON interview_sessions (application_id);


-- ── Saved Jobs ─────────────────────────────────────────────────────────────

CREATE TABLE saved_jobs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id      UUID        NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    fit_score   NUMERIC(4,2),
    notes       TEXT,
    saved_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_saved_jobs_unique
    ON saved_jobs (user_id, job_id);


-- ── Skill Analytics ────────────────────────────────────────────────────────
-- Replaces upskill/report-*.md flat file reports

CREATE TABLE skill_analytics (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill           TEXT        NOT NULL,
    gap_score       NUMERIC(5,2),                       -- weighted frequency score
    gap_type        TEXT,                               -- hard | domain | soft | tooling | credential
    priority        TEXT,                               -- critical | high | medium | low
    source_mode     TEXT,                               -- aggregate | targeted
    report_date     DATE        DEFAULT CURRENT_DATE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_skill_analytics_user
    ON skill_analytics (user_id, report_date DESC);


-- ── Notifications ──────────────────────────────────────────────────────────

CREATE TABLE notifications (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type        TEXT        NOT NULL,                   -- new_match | deadline_approaching | status_change
    title       TEXT        NOT NULL,
    body        TEXT,
    metadata    JSONB       DEFAULT '{}',
    is_read     BOOLEAN     DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_notifications_user
    ON notifications (user_id, is_read, created_at DESC);


-- ── Connector Health ───────────────────────────────────────────────────────

CREATE TABLE connector_health (
    connector               TEXT        PRIMARY KEY,
    last_success            TIMESTAMPTZ,
    last_failure            TIMESTAMPTZ,
    failure_count           INTEGER     DEFAULT 0,
    consecutive_failures    INTEGER     DEFAULT 0,
    error_message           TEXT,
    is_healthy              BOOLEAN     DEFAULT TRUE,
    avg_latency_ms          INTEGER     DEFAULT 0,
    jobs_seen               INTEGER     DEFAULT 0,
    jobs_inserted           INTEGER     DEFAULT 0,
    jobs_updated            INTEGER     DEFAULT 0,
    duplicates              INTEGER     DEFAULT 0,
    success_rate            NUMERIC(5,2) DEFAULT 100.0,
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);


-- ── Connector Runs ─────────────────────────────────────────────────────────

CREATE TABLE connector_runs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    connector       TEXT        NOT NULL,
    trigger         TEXT        NOT NULL,               -- scheduled | manual | webhook
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    jobs_found      INTEGER,
    jobs_new        INTEGER,
    jobs_updated    INTEGER,
    duration_ms     INTEGER,
    status          TEXT        DEFAULT 'running',      -- running | success | failed
    error           TEXT
);

CREATE INDEX idx_connector_runs_connector
    ON connector_runs (connector, started_at DESC);


-- ── Connector Errors ───────────────────────────────────────────────────────

CREATE TABLE connector_errors (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID        REFERENCES connector_runs(id),
    connector   TEXT        NOT NULL,
    source_url  TEXT,
    error_type  TEXT,
    message     TEXT,
    traceback   TEXT,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_connector_errors_run
    ON connector_errors (run_id);
CREATE INDEX idx_connector_errors_connector
    ON connector_errors (connector, occurred_at DESC);


-- ── Dead Letter Queue ──────────────────────────────────────────────────────

CREATE TABLE dead_letter_queue (
    id                  UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    connector           TEXT            NOT NULL,
    source_id           TEXT,
    idempotency_key     TEXT,
    payload             JSONB,
    exception_type      TEXT            NOT NULL,
    exception_message   TEXT            NOT NULL,
    stack_trace         TEXT,
    retry_count         INTEGER         DEFAULT 0,
    first_seen_at       TIMESTAMPTZ     DEFAULT NOW(),
    last_retry_at       TIMESTAMPTZ     DEFAULT NOW(),
    correlation_id      UUID,
    status              TEXT            NOT NULL DEFAULT 'NEW' -- NEW | RETRYING | IGNORED | RESOLVED
);


-- ── Embeddings ─────────────────────────────────────────────────────────────
-- Requires pgvector extension. Default dimension: 1536 (OpenAI text-embedding-3-small).
-- Change dimension if using a different embedding model.

CREATE TABLE job_embeddings (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id      UUID        NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    model       TEXT        NOT NULL,                   -- embedding model name
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_job_embeddings_job
    ON job_embeddings (job_id);
CREATE INDEX idx_job_embeddings_vec
    ON job_embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);                                 -- tune lists to sqrt(row_count)


CREATE TABLE company_embeddings (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id  UUID        NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    model       TEXT        NOT NULL,
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_company_embeddings_company
    ON company_embeddings (company_id);


CREATE TABLE user_embeddings (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    model       TEXT        NOT NULL,
    embedding   vector(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_user_embeddings_unique
    ON user_embeddings (user_id, model);


-- ── Audit Logs ─────────────────────────────────────────────────────────────

CREATE TABLE audit_logs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        REFERENCES users(id),
    action      TEXT        NOT NULL,                   -- e.g. "application.status_changed"
    entity_type TEXT,                                   -- "job" | "application" | "resume"
    entity_id   UUID,
    before      JSONB,
    after       JSONB,
    ip_address  INET,
    occurred_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user
    ON audit_logs (user_id, occurred_at DESC);
CREATE INDEX idx_audit_logs_entity
    ON audit_logs (entity_type, entity_id);


-- ── Foreign key back-fills (circular refs deferred to here) ───────────────

ALTER TABLE applications
    ADD CONSTRAINT fk_applications_resume
    FOREIGN KEY (resume_id) REFERENCES resumes(id);

ALTER TABLE applications
    ADD CONSTRAINT fk_applications_cover_letter
    FOREIGN KEY (cover_letter_id) REFERENCES cover_letters(id);
