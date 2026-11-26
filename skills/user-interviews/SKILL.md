---
name: user-interviews
description: Prepare and synthesize discovery interviews — a research plan tied to a decision, a screener that checks real behavior, an interview guide built on past events rather than opinions, and a synthesis that turns notes or transcripts into evidence-backed jobs, pains and opportunities with counts and quotes. Use when a feature idea lacks evidence, when a brief marks the problem as an assumption, when planning customer research, or when you have interview notes or transcripts to synthesize.
---

# User Interviews

Most feature ideas rest on what someone believes users want. Interviews replace belief with evidence — if they ask about what people actually did, not what they say they would do. This skill prepares interviews that produce facts, then turns the notes into findings the team can act on.

You prepare the plan, screener and guide, and you synthesize; the team runs the conversations. Work from the notes, transcripts or recordings' transcripts the user gives you access to.

## Phase 1: Plan around a decision

Read `brief.md` in the feature folder (`docs/product/<feature-slug>/`) when it exists, and write a short plan:

- **Decision** — what will the team decide with the answers? ("Build bulk invoicing this quarter, or not.") Research without a decision drifts.
- **Assumptions to test** — the beliefs the brief rests on, each phrased so an interview could disprove it.
- **What would change our mind** — the evidence that would make the team drop or reshape the idea.
- **Who** — the segments to hear from. Include people who don't use the product or stopped using it when the question is about adoption or churn.
- **How many** — 5 to 8 per segment to start. Stop when new interviews stop producing new themes.

## Phase 2: Write the screener

5 to 8 questions that qualify people on **behavior**, not self-description:

- Ask about recent actions: "In the last month, how did you bill your clients?" beats "Do you invoice often?".
- Include disqualifiers (competitors, employees, people interviewed recently) and a frequency check.
- Don't reveal the topic or the idea; people who know what you're looking for tend to give it to you.

## Phase 3: Write the interview guide

About 45 minutes. The interviewer talks less than 20 % of the time.

1. **Introduction (3 min)** — purpose without pitching, consent to record, "there are no right answers and we're not selling anything".
2. **Context (5 min)** — their role, their week, where this job fits.
3. **The last time (20 min)** — the core. "Tell me about the last time you <did the job>." Walk through it in order: what triggered it, which tools, who else was involved, what went wrong, how long it took, what it cost. Follow-ups: "What happened next?", "Why did that matter?", "Can you show me?"
4. **Workarounds and spend (10 min)** — what they've tried, paid for, built themselves or given up on. Money and time already spent are the strongest evidence of a real problem.
5. **Wrap-up (5 min)** — "What should I have asked?", and whether they can introduce someone else.

Questions to avoid, with what to ask instead:

| Avoid | Why | Ask instead |
|---|---|---|
| "Would you use a feature that…?" | Hypothetical; people are polite and optimistic | "When did this last happen? What did you do?" |
| "Would you pay for…?" | Answers don't predict behavior | "What do you pay for today to handle this?" |
| "Don't you find it frustrating when…?" | Leading | "How did that go?" |
| "What features do you want?" | Users describe solutions, not problems | "What were you trying to get done when that happened?" |

## Phase 4: Note-taking template

One sheet per interview, filled during or right after:

```markdown
## P3 — <segment>, <date>
**Context:** …
**Last time (story):** trigger → steps → outcome
**Pains:** "<verbatim quote>" — <what it cost: time, money, errors>
**Workarounds:** …
**Current spend:** tools, hours, people
**Surprises:** …
```

Number participants (P1, P2…). Keep names, emails and companies out of the notes that go into the repository; raw recordings and transcripts stay wherever the team stores research.

## Phase 5: Synthesize

From the notes or transcripts:

1. **Summarize each interview** with the template above, keeping verbatim quotes.
2. **Tag observations** — pain, workaround, trigger, goal, constraint — and cluster them into themes.
3. **Weigh each theme:**
   - **Frequency** — how many participants (3 of 8), per segment.
   - **Evidence strength** — a described past event or money spent is strong; an opinion or a wish is weak. Say which kind supports each theme.
   - **Intensity** — what the pain costs when it happens.
4. **Write job stories** for the strongest themes: "When <situation>, I want to <motivation>, so I can <outcome>."
5. **Rank opportunities** by frequency × intensity × fit with the product's direction.
6. **Report what contradicts the assumptions** from Phase 1. Disproved assumptions are the most valuable output; don't bury them.

Don't count a theme as validated because many people agreed with an idea when asked. Agreement is weak evidence; past behavior is strong evidence.

## Output

Write `research.md` to the feature folder: the plan, screener and guide before the interviews; then the synthesis with themes (frequency, evidence strength, quotes by participant ID), job stories, ranked opportunities, and disproved assumptions. Update the **Evidence** line of `brief.md` with what was learned. Summarize: the decision the research supports, the strongest finding, and the assumption that didn't survive.
