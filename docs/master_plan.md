# Helios: Personal Autonomous AI Career Agent (v2.0)

## Product Vision: Closed-Loop AI Employee

Helios is a **Personal Autonomous AI Career Agent** that acts as your dedicated job-hunting employee. It runs continuously, learns from every application attempt, and optimizes job search efficiency through a closed learning loop:

```
                          ┌───────────────────────────┐
                          │       Memory Agent        │
                          │ (History, Learnings, ATS) │
                          └─────────────┬─────────────┘
                                        │
                                        ▼
┌───────────────────┐        ┌────────────────────┐        ┌──────────────────┐
│  Discovery Agent  │───────►│  Filtering Agent   │───────►│  Ranking Agent   │
│ (Greenhouse,Lever,│        │ (Hard Rules &      │        │ (Skill Vectors & │
│  Ashby, Workday)  │        │  Rejection Logs)   │        │  Missing Skills) │
└───────────────────┘        └────────────────────┘        └────────┬─────────┘
                                                                    │
                                                                    ▼
┌───────────────────┐        ┌────────────────────┐        ┌──────────────────┐
│  Interview Agent  │◄───────│  Tracking Agent    │◄───────│ Application Agent│
│ (STAR Prep &      │        │ (Inbox & Status    │        │ (Playwright &    │
│  Dossiers)        │        │  CRM Sync)         │        │  Confidence Engine│
└───────────────────┘        └────────────────────┘        └──────────────────┘
```

---

## Key Innovations in Architecture

### 1. Memory Agent (The Central Brain)
- Remembers previously applied jobs to ensure zero duplicate applications.
- Stores historical answers to portal questions (e.g. sponsorship, notice period, salary expectations).
- Tracks resume version performance and company-specific interview feedback.
- Learns ATS-specific quirks (e.g., Workday form structure, Greenhouse success rate).

### 2. Confidence-Driven Automation Engine
- **Confidence ≥ 95%**: **Auto-Apply** (High match, standard ATS form, straightforward questions).
- **Confidence 80–94%**: **Ask User** (Sends Telegram/Desktop alert with 1-click "Approve & Submit").
- **Confidence < 80%**: **Needs Review** (Pushes to manual review queue with highlighted gaps).

### 3. Smarter Match Vector Breakdown & Missing Skill Alert
Rather than a single opaque score, the Ranking Agent outputs:
- **Overall Match**: `89%`
- **Sub-Score Breakdown**:
  - Python: `95%` | Backend Architecture: `91%` | LLMs: `87%` | Experience: `84%` | Location: `100%`
- **Missing Skills / Keywords**: `Docker`, `Redis` (Instantly flags skills to highlight in CV or upskill).

### 4. Opportunity Discovery & Rejection Transparency
Full visibility into filtered jobs to build system trust:
- `Found`: 127 jobs → `Rejected`: 109 → `Possible`: 14 → `Excellent Matches`: 4
- **Rejection Log**: "Rejected Job #482 because: Experience > 5 yrs, Requires US Citizenship, PHP role".

### 5. Focused ATS Core (Top 4 Tech Platforms)
Prioritize deep, reliable integration with the top 4 ATS platforms:
- **Greenhouse**
- **Lever**
- **Ashby**
- **Workday**

---

## Progress Assessment & MV-Agent Milestone

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PROGRESS TOWARD MV-AGENT SLICE                        │
│                                                                             │
│  Foundational Architecture & DB Schema ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░ 85%              │
│  Targeted ATS Connectors (Greenhouse/Lever) ▓▓▓▓▓▓▓▓▓▓▓▓░░░░ 60%           │
│  Resume Tailoring & LaTeX PDF Compiler ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░ 60%             │
│  Playwright Form Auto-Filler           ▓▓░░░░░░░░░░░░░░░░░░ 10%             │
│  Memory Agent & Confidence Engine      ▓▓▓▓░░░░░░░░░░░░░░░░ 20%             │
│                                                                             │
│  PROGRESS TOWARD CORE WORKFLOW SLICE: ~50% DONE | ~50% REMAINING            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Action Plan: Building the MV-Agent Vertical Slice

1. **Step 1**: Finalize Greenhouse + Lever JD extractor & Hard Rule Rejection Filter.
2. **Step 2**: Implement Smarter Match Agent (Skill vectors + Missing skill detection).
3. **Step 3**: Headless LaTeX PDF generator for targeted ATS resume & cover letter.
4. **Step 4**: Playwright browser automation agent for Greenhouse & Lever form auto-fill.
5. **Step 5**: Confidence engine + Telegram notification bot for 1-click human approval.
