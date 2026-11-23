# Job-to-Resume Match Scoring Rubric

This rubric is the **single source of truth** for evaluating how well a job posting aligns with the candidate's resume. The agent MUST apply it consistently and deterministically for every job. Total score: **0–100 points**.

---

## Category 1 — Tech Stack Match (40 points)

Evaluate the overlap between technologies listed in the job description and technologies demonstrated in `resume.md`.

### Scoring Breakdown

| Score | Criteria |
|-------|----------|
| **36–40** | 80%+ of required technologies are present in resume as proven experience (not just listed). The primary language and at least one major framework are an exact match. |
| **28–35** | 60–79% tech overlap. Primary language matches. 1–2 required technologies are missing but are closely adjacent (e.g., resume shows PostgreSQL, job requires MySQL). |
| **18–27** | 40–59% overlap. Primary language matches but several key frameworks or tools are absent or only tangentially mentioned. |
| **8–17** | 20–39% overlap. Significant gaps in required tech. Resume shows strong fundamentals but lacks domain-specific tools (e.g., job requires Rust, resume shows C++). |
| **0–7** | Less than 20% tech overlap. The role requires a fundamentally different stack. |

### Scoring Signals (positive)
- Exact language match (e.g., TypeScript ↔ TypeScript, not TypeScript ↔ JavaScript).
- Framework match at a major-version level (e.g., both require React 18+).
- Cloud provider match (AWS, GCP, Azure).
- Database paradigm match (relational, document, graph, time-series).
- Specific tooling match: CI/CD platforms, container orchestration, observability stacks.

### Scoring Signals (negative / deductions)
- Required tech listed in job is entirely absent from resume: **-3 pts per critical missing item** (up to 3 items; beyond 3, score floors at the band minimum).
- Technologies listed on resume are deprecated or version-locked in ways that signal unfamiliarity with modern idioms.

---

## Category 2 — Seniority & Experience Alignment (25 points)

Evaluate whether the role's seniority level, years-of-experience requirement, and scope of ownership match the candidate's background.

### Scoring Breakdown

| Score | Criteria |
|-------|----------|
| **22–25** | Exact seniority match. If the role is "Senior," the resume demonstrates 5+ years with ownership of systems, mentorship, and cross-functional collaboration. |
| **17–21** | One level off. Resume shows strong trajectory toward the role level (e.g., mid-level with senior projects, or senior applying for staff with partial IC-to-leadership signals). |
| **10–16** | Two levels off. Candidate could grow into the role within 6–12 months, but significant experience gaps exist. |
| **0–9** | Significant mismatch. The role is substantially above or below the candidate's demonstrated level. |

### Seniority Mapping Reference

| Title Keywords | Expected Signal in Resume |
|----------------|--------------------------|
| Junior / Associate | 0–2 years, guided contributions, learning trajectory |
| Mid / Software Engineer II | 2–5 years, owns features end-to-end, minimal supervision |
| Senior / Staff-adjacent | 5–8 years, system ownership, mentorship, cross-team influence |
| Staff / Principal | 8+ years, org-wide technical strategy, multiplier for teams |
| Lead / Engineering Manager | 5+ years, explicit people management or tech lead experience |

### Additional Signals
- **Ownership language in JD** ("you will own", "you will lead", "you will design from scratch"): requires resume to show equivalent initiative.
- **IC vs. Manager ambiguity**: if the JD blends both, default to IC scoring unless resume shows management experience.

---

## Category 3 — Remote / Contractor / LATAM Friendliness (20 points)

Evaluate whether the role is genuinely accessible to a remote, contractor, or LATAM-based candidate.

### Scoring Breakdown

| Score | Criteria |
|-------|----------|
| **18–20** | Explicitly remote-first globally, contractor or B2B contract acceptable, no timezone restrictions, or explicitly "LATAM welcome." |
| **13–17** | Remote allowed but timezone requirement is compatible (e.g., "Americas timezone" or "UTC-3 to UTC-8"). Full-time employment acceptable. |
| **7–12** | Remote allowed but timezone is restrictive (e.g., "PST preferred"), or unclear on contractor status. Requires further investigation. |
| **1–6** | Hybrid or on-site required. Relocation sponsorship not offered. LATAM not mentioned in an exclusionary context. |
| **0** | On-site only, specific country/state required, or the posting explicitly excludes the candidate's region. |

### Key Signals to Scan For

**Positive signals:**
- "Remote-first", "fully distributed", "work from anywhere"
- "B2B contract", "contractor", "freelance", "C2C"
- "Americas timezone", "UTC-3 to UTC-8", "LATAM"
- No explicit country restriction in the posting
- Company has existing team members in Latin America (infer from LinkedIn/About page if available)

**Negative signals:**
- "Must be authorized to work in [specific country]" with no contractor exception
- "On-site 3 days/week", "hybrid required"
- Explicit geo-block: "Not available in [region including LATAM countries]"
- "Must be a US resident / EU resident"

---

## Category 4 — Role Scope & Growth Signal (15 points)

Evaluate whether the role offers meaningful technical challenge, autonomy, and growth trajectory aligned with the candidate's goals.

### Scoring Breakdown

| Score | Criteria |
|-------|----------|
| **13–15** | The role involves greenfield or high-complexity systems work (distributed systems, platform engineering, new product lines). Clear engineering culture with ownership. |
| **9–12** | Established product with significant technical depth. Some ownership, some maintenance of legacy systems in a reasonable ratio. |
| **4–8** | Primarily maintenance or feature work on a mature product. Limited architectural ownership. Growth path is unclear. |
| **0–3** | CRUD/ticket-driven work. Technology choices are locked. No visible engineering culture signals. High turnover signals in the posting (overloaded requirements list, unusually high compensation without rationale). |

### Positive Growth Signals
- Mentions of open source contribution, internal tooling, or platform work.
- Engineering blog, public GitHub org, or conference presence.
- "You'll help define" / "you'll architect" language.
- Small-to-mid team size (5–50 engineers) — higher individual leverage.
- Recent funding round or healthy revenue signal.

### Negative / Red-Flag Signals
- Requirement list that spans 3+ pages or mixes 10+ frameworks.
- "Move fast" without engineering quality signals.
- No mention of code review, testing, or on-call practices.
- Vague compensation ("competitive salary") with no range disclosed.

---

## Final Score Interpretation

| Total Score | Recommendation |
|-------------|---------------|
| **90–100** | 🟢 **Top Tier** — Apply immediately. Prioritize outreach. |
| **80–89** | 🟢 **Strong Fit** — Generate outreach and tailoring. Flag for human review. |
| **65–79** | 🟡 **Moderate Fit** — Save for consideration. No outreach generated automatically. |
| **50–64** | 🟠 **Stretch Role** — Save only. Flag gaps for skill development. |
| **0–49** | 🔴 **Poor Fit** — Log and skip. Do not generate outreach. |

---

## Scoring Notes for the Agent

- Always cite the **specific evidence** from both the job description and `resume.md` that informed each score.
- When a signal is ambiguous (e.g., "remote possible"), default to the **lower end** of the scoring band and flag it explicitly.
- Never inflate a score to reach the 80-point outreach threshold. The rubric is a filter, not a sales tool.
- Round final scores to the nearest whole number. No decimals.
