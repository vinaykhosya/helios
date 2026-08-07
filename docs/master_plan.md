# Helios v3.0 — Autonomous AI Career Agent (Final Architecture)

## Product Definition

> **Helios is a Personal Autonomous AI Career Agent.**
> It discovers, evaluates, tailors, submits, and tracks job applications for you—24/7—while you sleep.
> You are notified only when human judgment is genuinely required.

---

## Architecture: System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                   MEMORY SERVICE                                        │
│  (Shared by all agents — every agent reads from and writes to memory independently)     │
│                                                                                         │
│  • Applied jobs log (never apply twice)                                                 │
│  • Historical questionnaire answers (sponsorship, notice period, salary)                │
│  • Resume version performance (which CV converted best, per company type)               │
│  • ATS portal quirks (Workday timeouts, Greenhouse field ordering)                      │
│  • Rejection/outcome history (rejected reasons, interview invites, offers)              │
└───────────┬──────────────┬──────────────────────────┬──────────────────────┬────────────┘
            │              │                          │                      │
            ▼              ▼                          ▼                      ▼
   ┌──────────────┐  ┌───────────────┐     ┌──────────────────┐   ┌────────────────────┐
   │   Profile    │  │   Discovery   │     │   Application    │   │  Tracking &        │
   │ Intelligence │  │    Agent      │     │     Agent        │   │  Interview Agent   │
   │   Agent      │  │               │     │                  │   │                    │
   └──────┬───────┘  └───────┬───────┘     └──────────────────┘   └────────────────────┘
          │                  │
          ▼                  ▼
   ┌──────────────────────────────────────────────────────┐
   │               Eligibility Gate                        │
   │  "Can Vinay apply?" (Hard rules — binary pass/fail)   │
   │  • Experience 0–3 yrs     • AI/ML/Python role         │
   │  • No sponsorship req     • Location match            │
   │  • Salary ≥ minimum       • No staffing agencies      │
   └──────────────────────────┬───────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────┐
   │               Ranking Agent                           │
   │  "Should Vinay apply?" (Soft scoring — 0–100%)        │
   │                                                       │
   │  Overall Match: 89%                                   │
   │  Python           ██████████ 95%                     │
   │  Backend Arch     █████████░ 91%                     │
   │  LLMs/AI          ████████░░ 87%                     │
   │  Experience       ████████░░ 84%                     │
   │  Location         ██████████ 100%                    │
   │                                                       │
   │  ⚠ Missing Keywords: Docker, Redis                    │
   └──────────────────────────┬───────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────┐
   │          Resume Tailoring Agent                        │
   │  • Pulls structured data from Profile Intelligence    │
   │  • Injects job-specific keywords from JD              │
   │  • Compiles ATS-optimised LaTeX PDF (headless)        │
   │  • Generates matching cover letter                    │
   └──────────────────────────┬───────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────┐
   │          Application Agent + Confidence Engine         │
   │                                                       │
   │  Confidence ≥ 95%  →  Auto-Apply                     │
   │  Confidence 80–94% →  Telegram / Desktop Alert        │
   │                        "Approve & Submit?"            │
   │  Confidence < 80%  →  Push to Manual Review Queue    │
   │                                                       │
   │  Stops automatically on:                              │
   │  • CAPTCHA detected       • OTP required              │
   │  • Sponsorship question   • Custom free-text field    │
   └──────────────────────────┬───────────────────────────┘
                              │
                              ▼
   ┌──────────────────────────────────────────────────────┐
   │     Tracking & Interview Concierge Agent               │
   │  • Scans Gmail/IMAP for replies, OAs, invites         │
   │  • Updates CRM status                                 │
   │  • Generates STAR interview dossier per company       │
   │  • Sets calendar reminders                            │
   └──────────────────────────────────────────────────────┘
```

---

## The 7 Agents (Final)

| Agent | Role | Key Decision |
|---|---|---|
| **Memory Service** | Shared persistent brain — not an agent | Every agent reads/writes independently |
| **Profile Intelligence** | Maintains structured candidate profile | Source of truth for all resume gen |
| **Discovery Agent** | Polls Greenhouse, Lever, Ashby, Workday | Focused on Big 4 ATS first |
| **Eligibility Gate** | Hard binary filter — "Can Vinay apply?" | Keeps ranking fast and focused |
| **Ranking Agent** | Soft scoring — "Should Vinay apply?" | Multi-dimensional skill breakdown |
| **Resume Tailoring Agent** | Headless LaTeX PDF generator | Consumes Profile Intelligence directly |
| **Application Agent** | Playwright browser automation + Confidence Engine | Pauses for sensitive inputs |
| **Tracking & Interview Agent** | Gmail scanner + interview dossier generator | Closes the feedback loop |

---

## The Daily Briefing (Core User Touchpoint)

```
☀  Good morning Vinay — 08:00

Yesterday Helios:
  ✓ Scanned    3,248 new job postings
  ✓ Eligible      87 (passed hard rules)
  ✓ Excellent     11 matches (score ≥ 85%)
  ✓ Applied        7 (confidence ≥ 95%)
  ⏳ Awaiting      2 (need your approval)
  📝 New OA        1 — deadline Friday
  🗓 Interview     Siemens — tomorrow 2pm

Most-missed keyword this week:  Docker
Resume version "v14-ml-focus" is outperforming all others.
```

---

## Honest Progress Assessment (3-Layer View)

```
Layer 1: Architecture & Design
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░  ~90% complete
Contracts, interfaces, events, DB schema, docs, ADRs — all defined.

Layer 2: Core Workflow Implementation
▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~40–50% complete
Connectors, normaliser, deduplicator, LaTeX templates — partially built.
Playwright, confidence engine, Memory Service — not yet started.

Layer 3: Production-Ready Personal AI Employee
▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~25–35% complete
Reliable cross-ATS automation, CAPTCHA edge cases, resume quality loop,
application failure recovery — this is where complexity lives.
```

> The hardest engineering is ahead: reliable ATS automation, dynamic form handling,
> and the resume → outcome feedback loop. Design is the easy part.

---

## MVP Vertical Slice (Build This First)

```
1. Greenhouse job posting arrives
       ↓
2. Eligibility Gate filters (hard rules)
       ↓
3. Ranking Agent scores (multi-dimensional)
       ↓
4. Profile Intelligence → Resume Tailoring → LaTeX PDF
       ↓
5. Playwright fills Greenhouse form
       ↓
6. Confidence Engine decides: auto-apply / alert / review
       ↓
7. Memory Service records outcome
       ↓
8. Morning Briefing includes this application
```

**When this single slice works reliably, Helios is genuinely useful.**
Everything else is expansion, not proof of concept.

---

## Focused ATS Strategy

Depth over breadth. These 4 platforms cover ~70% of tech companies.

| ATS | Priority | Notes |
|---|---|---|
| Greenhouse | 1 — First | JSON API well-documented |
| Lever | 2 | Similar structure to Greenhouse |
| Ashby | 3 | Growing rapidly in tech startups |
| Workday | 4 | Complex but high-value enterprise coverage |

*Add Wellfound, LinkedIn, Naukri, Foundit only after all 4 are stable.*
