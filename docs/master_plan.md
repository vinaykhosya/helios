# Helios: Autonomous AI Employee — Progress & Strategic Roadmap

## Product Vision: The Personal Autonomous Career Agent

Helios is pivoting from a passive job dashboard into a **Personal Autonomous AI Employee**. Helios operates silently in the background while you sleep:
1. **Discovers**: Scans 100+ sources every 6 hours.
2. **Filters (Quality First)**: Applies strict hard constraints (e.g., AI/Python roles, 0–3 yrs exp, minimum salary, no staffing agencies).
3. **Ranks**: Computes 0–100% fit scores using `pgvector` + LLM evaluation.
4. **Tailors**: Generates company-specific LaTeX PDFs for CV & cover letter.
5. **Auto-Applies**: Uses Playwright browser automation to fill form portals (Greenhouse, Lever, Ashby, Workday).
6. **Human-in-the-Loop**: Pauses ONLY for CAPTCHAs, OTPs, or custom questions, notifying you for 1-click approval.
7. **Interview Concierge & Briefing**: Monitors inbox for interview invites, updates application CRM status, generates interview dossiers, and delivers a daily Morning Executive Briefing.

---

## Progress Assessment: Where We Stand Today

### Overall Completion: ~35% Complete | ~65% Remaining

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CURRENT COMPLETION                               │
│                                                                             │
│  Foundational Architecture & DB Schema ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░ 85%              │
│  Discovery Agent (Connectors & Pipeline) ▓▓▓▓▓▓▓▓░░░░░░░░░░ 40%              │
│  Matching & Resume Tailoring Engines    ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░ 50%              │
│  Application Agent (Browser Auto-Fill)  ▓▓░░░░░░░░░░░░░░░░░ 10%              │
│  Email Concierge & Morning Briefing    ▓▓░░░░░░░░░░░░░░░░░ 10%              │
│                                                                             │
│  TOTAL PROGRESS: 35% DONE | 65% REMAINING                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Agent Breakdown

### Agent 1: Discovery Agent (Job Harvester)
- **Status**: **40% Complete**
- **Done**:
  - `BaseConnector` contract & `ConnectorRegistry`.
  - `GreenhouseConnector` & `LeverConnector` JSON adapters.
  - Job search CLI toolset for Jobindex, Jobbank, Jobnet, LinkedIn.
- **Remaining (60%)**:
  - Connectors for Ashby, Workday, Wellfound, Naukri, and direct career pages.
  - Continuous 6-hour scheduler daemon (`workers/ingestion_worker.py`).

---

### Agent 2: Matching Agent (Quality Matcher)
- **Status**: **50% Complete**
- **Done**:
  - Universal `Job` domain schema & normalization pipeline (`NormalizerStage`, `DeduplicatorStage`, `CompanyResolverStage`).
  - Strict rule model (`core/models/user.py`).
- **Remaining (50%)**:
  - Hard constraint rule filter (Salary, AI/Python, Exp 0–3 yrs, No staffing agencies).
  - Vector embeddings (`pgvector`) & 0–100% LLM match scoring stage (`RankerStage`).

---

### Agent 3: Resume & Cover Letter Agent (ATS Tailor)
- **Status**: **50% Complete**
- **Done**:
  - ModernCV LaTeX template & cover letter `cover.cls` template.
  - CLI compilation workflows (`lualatex` / `xelatex`).
- **Remaining (50%)**:
  - Headless background PDF compilation service (`ResumeService`).
  - Dynamic ATS keyword optimization per job description.

---

### Agent 4: Application Agent (Browser Auto-Filler & Human-in-the-Loop)
- **Status**: **10% Complete** (Highest Priority Gap)
- **Done**:
  - Application CRM state machine & data models.
- **Remaining (90%)**:
  - Playwright / Chromium browser automation scripts for Greenhouse, Lever, Ashby, and Workday forms.
  - Smart field auto-answer engine (work eligibility, notice period, expected salary, graduation year).
  - CAPTCHA / OTP / Custom Question detection & pause trigger.
  - Mobile/Desktop notification bot (Telegram/Email) with 1-click "Approve & Submit" trigger.

---

### Agent 5: Interview & Email Concierge Agent
- **Status**: **10% Complete**
- **Done**:
  - Interview preparation prompt templates and STAR framework.
- **Remaining (90%)**:
  - Inbox scanner (Gmail/IMAP API) to detect application responses, OAs, and interview invites.
  - Auto-generated STAR behavioral + technical interview briefing dossiers.
  - Morning Executive Briefing generator ("Good morning Vinay...").

---

## Revised Vertical Slice Execution Roadmap

```
Step 1: Hard Rules & Vector Ranker (Filter out 90% of noise)
   ↓
Step 2: Headless LaTeX PDF Generator (Generate targeted ATS CV)
   ↓
Step 3: Playwright Form Filler for Greenhouse & Lever (Auto-fill applications)
   ↓
Step 4: Human-in-the-Loop Pause & Telegram/Desktop Notification Bot
   ↓
Step 5: Morning Executive Briefing & Gmail Inbox Scanner
```
