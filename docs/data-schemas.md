# Data Schemas

All persistent data structures in Helios. Covers the 18 database tables and the flat-file formats inherited from the original `ai-job-search` repository.

---

## Database Tables (PostgreSQL)

### users

Candidate profiles. The `profile` JSONB column stores the structured output of `/setup` from the existing Claude Code engine.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | UUID | PK, DEFAULT | Auto-generated |
| email | TEXT | UNIQUE NOT NULL | Login identifier |
| name | TEXT | nullable | Display name |
| profile | JSONB | nullable | Structured candidate profile (education, experience, skills, goals) |
| settings | JSONB | DEFAULT '{}' | UserSettings (notifications, preferences) |
| target_roles | TEXT[] | nullable | e.g. ["Data Scientist", "ML Engineer"] |
| target_locations | TEXT[] | nullable | e.g. ["Copenhagen", "Remote"] |
| skills | TEXT[] | nullable | Extracted from profile |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Updated by trigger on change |

---

### companies

Enriched company profiles. Created by `CompanyResolverStage` when a new company appears in a job posting.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| name | TEXT NOT NULL | Original name from job posting |
| name_normalized | TEXT UNIQUE | Lowercase, legal suffixes stripped (A/S, GmbH, Inc.) |
| website | TEXT | |
| industry | TEXT | |
| size | TEXT | "1-10" \| "11-50" \| "51-200" \| "201-500" \| "501-1000" \| "1001+" |
| description | TEXT | |
| logo_url | TEXT | |
| linkedin_url | TEXT | |
| glassdoor_url | TEXT | |
| headquarters | TEXT | |
| founded_year | INTEGER | |
| salary_data | JSONB | From `salary_lookup.py` integration |
| tech_stack | TEXT[] | Enriched from LinkedIn/Clearbit |
| created_at / updated_at | TIMESTAMPTZ | |

---

### jobs

The central table. Populated by `PersistenceStage`. Every row corresponds to one `Job` Pydantic model instance.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| source | TEXT NOT NULL | Connector name (jobindex, greenhouse, linkedin, …) |
| source_id | TEXT NOT NULL | Portal-native job ID |
| source_url | TEXT NOT NULL | Canonical URL on the portal |
| title | TEXT NOT NULL | Normalized job title |
| description | TEXT | Full job description (HTML stripped) |
| company_id | UUID FK → companies | Set by CompanyResolverStage |
| company_name | TEXT NOT NULL | Denormalized for fast reads |
| location | TEXT | Raw location string from portal |
| city | TEXT | |
| country | TEXT | DEFAULT 'Denmark' |
| remote | TEXT | on_site \| remote \| hybrid |
| relocation_supported | BOOLEAN | DEFAULT FALSE |
| visa_sponsorship | BOOLEAN | DEFAULT FALSE |
| employment_type | TEXT | full_time \| part_time \| contract \| freelance \| internship |
| seniority | TEXT | junior \| mid \| senior \| lead \| principal |
| experience_years | INTEGER | Minimum years required |
| education_required | TEXT | |
| security_clearance | BOOLEAN | |
| languages_required | TEXT[] | |
| salary_min | INTEGER | In salary_currency units |
| salary_max | INTEGER | |
| salary_currency | TEXT | DEFAULT 'DKK' |
| salary_raw | TEXT | Original salary string from posting |
| salary_confidence | TEXT | explicit \| estimated \| unknown |
| benefits | TEXT[] | |
| skills | TEXT[] | GIN-indexed for fast filtering |
| industry | TEXT | |
| posted_date | TIMESTAMPTZ | |
| deadline | TIMESTAMPTZ | |
| apply_url | TEXT | Direct application URL |
| is_active | BOOLEAN | FALSE when job expires or is removed |
| raw_data | JSONB | Original connector payload, preserved for re-parsing |
| fetched_at | TIMESTAMPTZ | When the connector fetched this job |
| created_at | TIMESTAMPTZ | When Helios first stored this job |

**Indexes:** `(source, source_id)` unique, `company_id`, `posted_date DESC`, `deadline`, `is_active`, `skills` GIN, `(city, country)`.

---

### applications

Replaces `job_search_tracker.csv`. One row per user–job application.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| job_id | UUID FK → jobs | |
| status | TEXT | saved \| applied \| phone_screen \| technical \| case \| final \| offer \| offer_declined \| rejected \| withdrawn \| no_response |
| applied_at | TIMESTAMPTZ | When the user submitted the application |
| resume_id | UUID FK → resumes | Set after resume is generated |
| cover_letter_id | UUID FK → cover_letters | Set after cover letter is generated |
| fit_rating | NUMERIC(4,2) | 0.00–1.00, from evaluation step |
| notes | TEXT | Free-form notes |
| contact_person | TEXT | Hiring manager or recruiter name |
| source_channel | TEXT | How the job was found (jobindex, linkedin, referral, …) |
| created_at / updated_at | TIMESTAMPTZ | |

**CSV equivalent:** Maps directly to `job_search_tracker.csv` columns: `date→applied_at`, `company→jobs.company_name`, `role→jobs.title`, `fit_rating`, `notes`, `cv_file→resume_id`, `cover_letter_file→cover_letter_id`, `source→source_channel`.

---

### resumes

Generated resume documents (LaTeX source + compiled PDF path).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| job_id | UUID FK → jobs | NULL = master resume |
| file_path | TEXT | Path to compiled PDF |
| latex_source | TEXT | Full LaTeX source |
| version | INTEGER | Increments on each regeneration |
| is_master | BOOLEAN | TRUE = user's base template |
| created_at | TIMESTAMPTZ | |

---

### cover_letters

Generated cover letter documents.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| job_id | UUID FK → jobs | |
| file_path | TEXT | Path to compiled PDF |
| latex_source | TEXT | Full LaTeX source |
| version | INTEGER | |
| language | TEXT | DEFAULT 'en' (Danish = 'da') |
| created_at | TIMESTAMPTZ | |

---

### interview_sessions

AI-generated interview preparation sessions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| application_id | UUID FK → applications | |
| stage | TEXT | phone \| technical \| case \| final |
| questions | JSONB | [{question, category, difficulty}] |
| answers | JSONB | [{question_id, answer, star_structure}] |
| talking_points | TEXT | Free-form talking points |
| scheduled_at | TIMESTAMPTZ | Interview date/time |
| created_at | TIMESTAMPTZ | |

---

### saved_jobs

User's job wishlist. Jobs a user wants to review but hasn't applied to.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| job_id | UUID FK → jobs | |
| fit_score | NUMERIC(4,2) | At time of saving |
| notes | TEXT | |
| saved_at | TIMESTAMPTZ | |

Unique constraint: `(user_id, job_id)`.

---

### skill_analytics

Replaces `upskill/report-*.md` flat files. One row per skill gap per report run.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| skill | TEXT | Skill name |
| gap_score | NUMERIC(5,2) | Weighted frequency score |
| gap_type | TEXT | hard \| domain \| soft \| tooling \| credential |
| priority | TEXT | critical \| high \| medium \| low |
| source_mode | TEXT | aggregate \| targeted |
| report_date | DATE | |
| created_at | TIMESTAMPTZ | |

---

### notifications

In-app and queued email notifications.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | |
| type | TEXT | new_match \| deadline_approaching \| status_change \| run_failed |
| title | TEXT | |
| body | TEXT | |
| metadata | JSONB | e.g. {job_id, fit_score, deadline} |
| is_read | BOOLEAN | DEFAULT FALSE |
| created_at | TIMESTAMPTZ | |

---

### connector_health

Current health status of each registered connector.

| Column | Type | Description |
|--------|------|-------------|
| connector | TEXT PK | Connector name |
| last_success | TIMESTAMPTZ | |
| last_failure | TIMESTAMPTZ | |
| failure_count | INTEGER | Resets to 0 on success |
| error_message | TEXT | Last error message |
| is_healthy | BOOLEAN | FALSE if failure_count > threshold |
| updated_at | TIMESTAMPTZ | |

---

### connector_runs

Historical record of every connector execution.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| connector | TEXT | |
| trigger | TEXT | scheduled \| manual \| webhook |
| started_at | TIMESTAMPTZ | |
| completed_at | TIMESTAMPTZ | |
| jobs_found | INTEGER | Total from portal |
| jobs_new | INTEGER | After deduplication |
| jobs_updated | INTEGER | Existing jobs with changed fields |
| duration_ms | INTEGER | |
| status | TEXT | running \| success \| failed |
| error | TEXT | Set on failure |

---

### connector_errors

Individual errors within a connector run.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| run_id | UUID FK → connector_runs | |
| connector | TEXT | |
| source_url | TEXT | URL that caused the error |
| error_type | TEXT | Exception class name |
| message | TEXT | |
| traceback | TEXT | Full traceback |
| occurred_at | TIMESTAMPTZ | |

---

### job_embeddings

Vector embeddings for jobs (used by RankerStage).

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| job_id | UUID FK → jobs | |
| model | TEXT | e.g. "text-embedding-3-small" |
| embedding | vector(1536) | pgvector column |
| created_at | TIMESTAMPTZ | |

IVFFlat index for approximate nearest-neighbour search.

---

### company_embeddings / user_embeddings

Same structure as `job_embeddings`, for companies and users respectively.
`user_embeddings` has a unique constraint on `(user_id, model)` — one embedding per user per model.

---

### audit_logs

Immutable record of all state-changing actions.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID PK | |
| user_id | UUID FK → users | Actor (NULL for system actions) |
| action | TEXT | e.g. "application.status_changed" |
| entity_type | TEXT | "job" \| "application" \| "resume" \| … |
| entity_id | UUID | The affected entity |
| before | JSONB | State before the action |
| after | JSONB | State after the action |
| ip_address | INET | |
| occurred_at | TIMESTAMPTZ | |

---

## Flat-File Formats (Legacy / Compatibility)

These are preserved from the original `ai-job-search` repository and may be read during Phase 2 migration tooling.

### job_search_tracker.csv

```
date, company, sector, role, role_type, channel, status, contact_person,
fit_rating, notes, cv_file, cover_letter_file, source
```

Maps to: `applications` table (see `applications` entry above for column mapping).

### job_scraper/seen_jobs.json

```json
{
  "seen": {
    "<url_or_company_title_key>": {
      "title": "...",
      "company": "...",
      "url": "...",
      "first_seen": "YYYY-MM-DD",
      "fit": "high/medium/low",
      "status": "new/skipped/evaluated"
    }
  }
}
```

Replaced by: `jobs` table (deduplication via `source + source_id`) + `saved_jobs` table.

### salary_data.json

```json
{
  "metadata": {"source": "...", "currency": "DKK", "year": 2025},
  "companies": [
    {
      "name": "Company A/S",
      "aliases": ["Company"],
      "salary": {"min": 550000, "max": 700000, "period": "annual"}
    }
  ]
}
```

Read by `salary_lookup.py`. In Helios, equivalent data is stored in `companies.salary_data` JSONB.
