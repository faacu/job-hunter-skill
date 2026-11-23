# Outreach Writing Guidelines

Rules for generating cold emails and LinkedIn DMs that read like a message from a **peer engineer**, not a recruiter or a bot.

---

## Core Philosophy

The goal is a 90-second read that makes a senior engineer or EM think:
> "This person did their homework and might actually be useful. I'll reply."

You are **not** selling. You are opening a technical conversation between peers. The message signals that you understand their system, their problem space, and can contribute — without begging, bragging, or wasting their time.

---

## Structural Template

```
Subject: <specific, non-generic, 6–10 words>

<Opening line: a specific observation about their tech or product — not a compliment.>

<1–2 sentences: the concrete overlap between your experience and their actual problem.>

<1 sentence: the ask — low friction, easy to say yes to.>
```

**Total length:** 80–120 words for the body. Never exceed 150 words.

---

## Subject Line Rules

**DO:**
- Reference something specific: a tech choice, a blog post title, an open-source repo they maintain.
- Use the engineer's or EM's name when possible.
- Be direct about the purpose.

**Examples of good subject lines:**
- `Re: Your migration from Kafka to Redpanda at scale`
- `Re: gRPC + Go at [Company] — potential fit`
- `Quick question on your platform team's approach to multi-tenancy`

**DO NOT:**
- Use "Exciting opportunity", "Reaching out", "Following up", "Hope this finds you well".
- Write a subject line that could apply to any company.
- Use emojis or excessive punctuation.

---

## Opening Line Rules

The opening line must be **specific and technical**. It should reference something verifiable about the company:
- A recent engineering blog post or talk.
- A specific technology decision visible in their public repos or job description.
- A product challenge that is evident from their user-facing product.

**DO:**
> "I read your post on migrating from a monolith to event-driven microservices using Kafka — the write-amplification tradeoffs you described in Phase 2 are exactly what we ran into at [previous company]."

> "Your job description mentions owning the data pipeline from ingestion to Redshift — that's the core of what I built for the last 3 years."

**DO NOT:**
> "I came across your company and was really impressed by what you're building."

> "Your company is doing amazing things in the [industry] space."

> "I'm very passionate about [generic domain]."

---

## Body Copy Rules

### What to include
- **One specific parallel**: A concrete overlap between your past work and their evident technical problem. Use numbers where possible.
- **One forward-looking statement**: What you would bring to or do in their context, stated as a hypothesis, not a promise.

**Example:**
> "I spent the last two years owning the backend for a real-time scoring API serving 50M events/day on GCP. The load-shedding and idempotency patterns we developed would map directly to what your infrastructure JD describes."

### What to never include
- Adjectives about yourself: "passionate", "driven", "motivated", "excited", "enthusiastic".
- Vague capability claims: "I'm a fast learner", "I thrive in fast-paced environments".
- Lists of technologies — this belongs in the resume, not the message.
- Requests for the job: never say "I'm applying for" or "I want the role" — the goal is a conversation, not a submission.

---

## Call to Action (CTA) Rules

The CTA should be **low-friction** and **specific**. The ideal ask has a yes/no answer or a 15-minute time commitment.

**Good CTAs:**
- "Would a 15-minute call this week or next make sense?"
- "Happy to share more context on the pipeline architecture — does that seem relevant to what your team is solving?"
- "If the team is exploring options, I'd be glad to do a quick technical screen to see if the overlap is real."

**Bad CTAs:**
- "Please let me know if there are any openings." (passive, no action)
- "I look forward to hearing from you." (filler)
- "I would love the opportunity to join your incredible team." (sycophantic)
- "Feel free to reach out at any time." (vague, shifts all effort to them)

---

## Banned Words & Phrases

The following words and phrases are **strictly prohibited** in outreach messages. Their presence signals AI generation and will cause the message to be discarded.

| Category | Banned |
|----------|--------|
| AI buzzwords | passionate, excited, thrilled, innovative, cutting-edge, game-changing, disruptive, leverage (as a verb), synergy, robust solution, seamlessly |
| Filler openers | Hope this finds you well, I wanted to reach out, I came across your profile, I'm following up |
| Self-promotion | fast learner, team player, detail-oriented, results-driven, self-motivated, out-of-the-box thinker |
| Vague claims | strong background in, extensive experience with, proven track record |
| Closing fluff | Looking forward to your response, Thank you for your time and consideration, I appreciate your consideration |

---

## Tone Reference

Write as if you are a senior engineer sending an internal Slack message to an engineering manager you've met at a conference. The register is:
- **Professional but casual** — no formal salutations ("Dear", "To Whom It May Concern").
- **Direct** — state what you're doing and why in the first sentence.
- **Specific** — every sentence should contain one verifiable fact.
- **Peer-level** — do not perform deference or enthusiasm.

---

## Platform-Specific Notes

### Cold Email
- Use first name in the greeting: "Hi [Name]," (not "Hello", not "Hi there").
- Include a plain-text signature with your name, LinkedIn URL, and GitHub URL.
- Do not attach the resume to the first email. Offer it upon request.

### LinkedIn DM
- Skip the greeting entirely — LinkedIn DMs are conversational by nature.
- The character limit for connection request notes is 300 characters. Keep it to one specific sentence + one question.
- For InMail, follow the full template but keep it tighter (100 words max).

---

## Quality Checklist (Agent Self-Verification)

Before finalizing an outreach draft, the agent MUST verify all of the following:

- [ ] Word count is between 80–120 words (body only, excluding subject line and signature).
- [ ] No banned words or phrases from the list above are present.
- [ ] The opening line references a specific, verifiable fact about the company or role.
- [ ] At least one sentence contains a quantified or concrete technical claim from the candidate's resume.
- [ ] The CTA asks for something that can be answered in one sentence.
- [ ] The message does not contain the word "apply", "application", "job", or "position" in a submissive context.
- [ ] The tone is peer-level — not deferential, not boastful.

If any item fails, regenerate the failing section before presenting the draft to the user.
