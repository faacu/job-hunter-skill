---
name: job-hunter-skill
description: >
  A cross-platform agent skill that automates the remote tech job search and
  outreach workflow using Firecrawl MCP for discovery, deterministic resume
  match scoring, and peer-to-peer outreach generation — with a strict
  human-in-the-loop guardrail that prevents any unattended submissions.
triggers:
  - "find remote jobs"
  - "search for tech jobs"
  - "job hunt"
  - "find engineering roles"
  - "search job boards"
  - "look for remote software jobs"
  - "find jobs on Greenhouse"
  - "find jobs on Ashby"
  - "find jobs on Lever"
  - "find jobs on Workable"
  - "score job posting"
  - "evaluate job fit"
  - "write cold email for job"
  - "tailor resume for job"
---

# Job Hunter Skill

## Overview

This skill automates the remote tech job search pipeline. It uses **Firecrawl MCP** to scrape modern startup ATS platforms, scores each listing against your local `resume.md` using a structured rubric, generates tailored outreach for high-fit roles, and tracks everything in a local SQLite database — all without sending your data to any server.

**BYOK (Bring Your Own Key):** Bring your own Firecrawl API key. Zero hosting costs.

---

## Prerequisites

Before executing this skill, verify the following are in place:

1. **`resume.md`** — Your resume in Markdown format, located at the project root (see `examples/resume.example.md` for the expected structure). This file is `.gitignore`d and never committed.
2. **Firecrawl MCP** — Configured in your agent's MCP settings with a valid `FIRECRAWL_API_KEY`.
3. **Tracker initialized** — Run `python scripts/tracker.py init` once to create the local `jobs.db` SQLite database.
4. **Python 3.10+** — Required for `scripts/tracker.py`.

---

## Trigger Conditions

Activate this skill when the user asks to:
- Search for remote software engineering jobs on startup ATS platforms.
- Score a specific job posting against their resume.
- Generate a tailored cold email or outreach message for a job.
- Check if a job URL has already been processed.
- View the status of tracked applications.

---

## Execution Instructions

### Phase 1 — Targeted Job Discovery

1. Use **Firecrawl MCP** (`firecrawl_scrape` or `firecrawl_crawl`) to search the following ATS platforms for **remote software engineering roles posted in the last 7 days**:
   - `https://boards.greenhouse.io/`
   - `https://jobs.ashbyhq.com/`
   - `https://jobs.lever.co/`
   - `https://apply.workable.com/`

2. For each search, use query parameters or site-specific filters to narrow results:
   - Keywords: `"remote"`, `"senior software engineer"`, `"backend"`, `"full-stack"` (adapt to user's target role from `resume.md`).
   - Date filter: last 7 days where the platform supports it.

3. Collect each job posting as a structured record:
   ```
   - url: <canonical job URL>
   - company: <company name>
   - title: <job title>
   - platform: <greenhouse|ashby|lever|workable>
   - posted_date: <ISO date if available, else "unknown">
   - description: <full job description text>
   ```

4. **Deduplication check** — Before scoring, verify each URL is not already tracked:
   ```bash
   python scripts/tracker.py check --url "<job_url>" --json
   ```
   Parse the JSON response. If `"exists": true`, **skip** this job and log: `[SKIP] Already tracked: <url>`. Proceed only when `"exists": false`.

---

### Phase 2 — Deterministic Match Scoring

For each untracked job posting, score it against `resume.md` using the rubric defined in `references/scoring-rubric.md`.

The rubric produces a **total score from 0 to 100** across four weighted categories:
- **Tech Stack Match** (40 pts)
- **Seniority & Experience Alignment** (25 pts)
- **Remote / Contractor / LATAM Friendliness** (20 pts)
- **Role Scope & Growth Signal** (15 pts)

Produce a structured score breakdown for every job:
```
Job: <title> at <company>
URL: <url>
Score: <total>/100
  - Stack Match:        <pts>/40
  - Seniority:          <pts>/25
  - Remote/LATAM:       <pts>/20
  - Scope & Growth:     <pts>/15
Rationale: <1–2 sentence summary of fit>
```

Add every scored job to the tracker:
```bash
python scripts/tracker.py add \
  --url "<job_url>" \
  --company "<company>" \
  --title "<title>" \
  --score <score> \
  --platform "<platform>"
```

---

### Phase 3 — Outreach & Tailoring (Score >= 80)

For jobs scoring **80 or above**, generate two outputs:

#### 3a. Resume Tailoring Suggestions
Produce a bullet-point list of specific, actionable edits to `resume.md` to better align with the job description. Focus on:
- Keywords from the job description missing in the resume.
- Reordering or emphasizing relevant experience sections.
- Quantifying achievements that match the role's expectations.

Do **not** rewrite the entire resume — output targeted diffs only.

#### 3b. Cold Outreach Message
Using the guidelines in `references/outreach-guidelines.md`, generate a concise, peer-to-peer cold email or LinkedIn DM targeting the **Engineering Manager or Hiring Manager** (not HR/Talent). The message must:
- Be under 120 words.
- Open with a specific technical observation about the company or role.
- State one concrete mutual benefit.
- End with a low-friction CTA.
- Avoid all AI-sounding buzzwords listed in the outreach guidelines.

Output format:
```
Subject: <email subject line>
---
<message body>
```

---

### Phase 4 — Human Review & Confirmation Gate

> **⛔ HARD STOP — MANDATORY HUMAN REVIEW**
>
> At this stage, the agent MUST present all collected data to the user and **WAIT for explicit confirmation** before any further action.

Present a consolidated summary table:
```
| # | Company | Title | Score | Platform | URL |
|---|---------|-------|-------|----------|-----|
| 1 | ...     | ...   | 95    | Ashby    | ... |
```

For each high-scoring job (>= 80), also present the tailoring suggestions and outreach draft.

**Then ask the user:**
> "Which of these jobs would you like to apply to? Please confirm by number. I will then prepare the final application materials for your manual review and submission."

**The agent MUST NOT:**
- Submit any application form automatically.
- Send any email or message without explicit user confirmation.
- Call any "apply" or "submit" endpoint on any ATS platform.
- Proceed past this phase without user input.

---

### Phase 5 — Status Tracking (Post-Confirmation)

Once the user confirms which jobs to pursue, update the tracker status:
```bash
# After user confirms intent to apply
python scripts/tracker.py update --url "<job_url>" --status APPLIED

# When user reports interview scheduled
python scripts/tracker.py update --url "<job_url>" --status INTERVIEWING

# When user reports rejection
python scripts/tracker.py update --url "<job_url>" --status REJECTED
```

To list the current pipeline at any time:
```bash
python scripts/tracker.py list --json
```

---

## Guardrails & Constraints

| Rule | Enforcement |
|------|-------------|
| No auto-submit | Agent terminates at Phase 4 pending human input |
| No PII leakage | `resume.md` is local-only; never passed to external APIs beyond the AI context window |
| No duplicate processing | Every URL is checked via `tracker.py check` before scoring |
| BYOK only | No credentials stored in this repo; all keys via environment variables |
| Scoring is deterministic | Rubric in `references/scoring-rubric.md` is the single source of truth |

---

## File Map

```
job-hunter-skill/
├── SKILL.md                        ← This file
├── resume.md                       ← Your local resume (gitignored)
├── jobs.db                         ← SQLite tracker DB (gitignored)
├── references/
│   ├── scoring-rubric.md           ← Scoring criteria (0–100)
│   └── outreach-guidelines.md      ← Outreach writing rules
├── scripts/
│   └── tracker.py                  ← CLI tracker (zero external deps)
├── tests/
│   └── test_tracker.py             ← pytest suite
├── examples/
│   └── resume.example.md           ← Resume template
├── README.md
├── LICENSE
└── .gitignore
```

---

## Installation

### Claude Code
```bash
mkdir -p ~/.claude/skills
cp -r job-hunter-skill ~/.claude/skills/
```
Reference in CLAUDE.md: `@~/.claude/skills/job-hunter-skill/SKILL.md`

### Cursor
Add to `.cursor/rules/` or reference via `@file` in the chat:
```
@job-hunter-skill/SKILL.md
```

### Antigravity / Gemini
Copy to your skills directory:
```bash
cp -r job-hunter-skill ~/.gemini/config/skills/
```
The skill auto-loads from that path on agent startup.
