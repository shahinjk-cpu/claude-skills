---
name: feature-brief
description: Frame a feature before it is built — the user problem, a job story, one success metric with baseline and target, the adoption hypothesis, a click budget for the happy path, scope cuts, and kill criteria. Use when starting a new feature, epic or ticket, when someone says "we should build X", or when a spec has no measurable goal.
---

# Feature Brief

Turn a feature idea into a one-page brief that says who it is for, how we will know it worked, and when we will stop. Most failed features weren't wrong in the code — they had no measurable goal, so nobody noticed they weren't used.

The brief is the root document of the feature folder: `docs/product/<feature-slug>/brief.md`, or wherever the project already keeps product docs. The other skills in this set read it — `happy-path-audit` takes its task and click budget, `instrument-feature` its metrics, `ab-test-design` its hypothesis.

## Phase 1: Read before asking

Read what already exists: the ticket or PRD, linked discussions, the code the feature touches, existing analytics events and dashboards, the feature-flag setup, and any earlier files in the feature folder. Note what the codebase tells you for free: who can reach this screen (roles, plans), what data already exists, what the current workaround looks like.

## Phase 2: Ask what only the user knows

Ask one consolidated round of questions, limited to what changes the brief:

- **Who** — which segment, role or plan? First-time or returning users?
- **Evidence** — what shows the problem is real (support tickets, interviews, data, churn reasons)? "Nothing yet" is a valid answer; the brief will mark it as an assumption, and `user-interviews` can gather the evidence.
- **Success** — what would make this worth it in six weeks? Push from outputs ("feature shipped") to outcomes ("teams send their first invoice in under two minutes").
- **Constraints** — deadline, platforms, what's off limits.

Offer choices with a "decide for me" option where you can propose a sensible default. Don't ask what the code or the ticket already answers.

## Phase 3: Write the brief

Use this structure. Keep it to one screen and cut any section with nothing real in it.

```markdown
# <Feature name>

**Problem.** <One sentence, in the user's words.>
**Evidence.** <Data, tickets, quotes — or "Assumption: not yet validated.">

**Job story.** When <situation>, I want to <motivation>, so I can <outcome>.
**Today's workaround.** <What users do now and what it costs them: time, clicks, errors, money.>

## Success
| Metric | Type | Baseline | Target | By |
|---|---|---|---|---|
| <% of active teams that send ≥ 1 invoice> | Primary | <value, or "unknown — measure first"> | <value> | <date> |
| <support tickets tagged "invoicing"> | Guardrail | | must not rise | |
| <first invoice within 7 days of signup> | Leading | | | |

## Adoption hypothesis
- **Eligible users:** <who should use it, and how many>
- **Discovery:** <where they'll find it, at the moment they need it>
- **Value moment:** <the action that proves value — not "opened the page">

## Happy path
<Start state → numbered steps → goal state.>
**Budget:** ≤ <N> clicks, ≤ <M> fields.

## Scope
- **In:** …
- **Out, and why:** …
- **Later:** …

## Rollout and kill criteria
- Behind flag `<name>`; ramp plan <…>; A/B test: yes/no, and why.
- **Kill or rework if** <primary metric> < <threshold> by <date>.

## Risks and open questions
- …
```

## Phase 4: Challenge the brief

Check the draft against these failure modes and fix or flag each one:

1. **Unmeasurable metric.** Can the primary metric be computed from events that exist today? If not, `instrument-feature` is a prerequisite — say so.
2. **Vanity metric.** Page views, clicks on the entry point and "users who saw it" measure exposure, not value. Replace them with the value moment.
3. **Cheaper solution.** Could a copy change, a better default, or surfacing an existing feature solve the problem? Say so. It's the most valuable sentence a brief can contain. When demand itself is the open question, propose a fake-door test first: the entry point ships alone, counts the clicks, and tells users honestly that the feature is coming.
4. **Solution posing as a problem.** "Users need a dashboard" is a solution. Rewrite it as the need.
5. **No kill criterion.** A feature without one is never removed. Pick a threshold the team would genuinely act on; `launch-review` checks it at the review date.
6. **No budget.** If the happy path has no click budget, estimate one now; `happy-path-audit` will refine it.

## Output

Write `brief.md` to the feature folder. Summarize in three lines: the primary metric and its target, the biggest assumption, and the next skill to run — usually `happy-path-audit` when the flow exists, or `instrument-feature` when the baseline is unknown.
