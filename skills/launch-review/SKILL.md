---
name: launch-review
description: Check a shipped feature against what its brief promised — verify the data can be trusted, pull the real numbers for the primary metric, guardrails and adoption funnel, compare them with the targets and kill criteria, find the first broken funnel stage, and recommend keep, rework or remove, with flag and code cleanup. Use when a feature reaches its review date or has been live for a few weeks, when someone asks "is this feature working?", or before investing more in a feature.
---

# Launch Review

A brief with a target and a kill criterion is only useful if someone comes back to check. Without that review, features that missed their goal stay in the product forever, costing maintenance and attention. This skill is the review: it compares what was promised with what happened, and ends with a decision.

## Phase 1: Gather the promises

Read the feature folder (`docs/product/<feature-slug>/`):

- `brief.md` — the primary metric, its baseline and target, guardrails, the kill criterion and the review date.
- `adoption-plan.md` — targets for each funnel stage.
- `tracking-plan.md` — the events and funnel definitions to query.
- `experiment.md` — if the feature was A/B tested, `experiment-readout` has already answered whether it caused the change. This review covers what happened after the full rollout.

Without a brief, reconstruct the goal with the user and label the review as made without targets set in advance — it's weaker evidence, and the summary should say so.

## Phase 2: Check that the data can be trusted

Before reading any result:

- **Tracking health** — daily event volumes since launch: no gaps, no sudden drops. A drop to zero is a broken event, not users leaving.
- **Rollout** — what share of eligible users actually had the feature, and since when. Don't compare a week at 10 % rollout with targets set for 100 %.
- **Denominator** — rates computed on eligible users, not on all users.
- **Context** — marketing campaigns, seasonality, pricing changes or incidents during the period that could explain the numbers on their own.

## Phase 3: Pull the numbers

Sources, in order of preference: a warehouse query, the analytics tool's API or a connected integration, an export, numbers the user pastes. Label every value as measured, and note the query or report it came from.

| Metric | Target | Actual | Status | Source |
|---|---|---|---|---|
| Primary: % of active teams that sent ≥ 1 invoice | 30 % | 22 % | Missed | warehouse query in appendix |
| Guardrail: invoicing support tickets per week | ≤ 15 | 9 | Met | helpdesk export |
| Funnel: reach (exposed ÷ eligible) | 80 % | 41 % | Missed | analytics funnel "invoicing-adoption" |

A before/after comparison is not proof that the feature caused the change. Say so, and compare with a holdout or a similar cohort when one exists.

## Phase 4: Diagnose

When targets are missed, find the **first** funnel stage with a sharp drop and work on that one: low exposure, low trial, low activation, low repeat use and low retention have different causes and fixes (see the diagnosis table in `adoption-plan`).

Then look for the why:

- **Segments** — who did adopt? Adoption concentrated in a segment other than the target one is a finding in itself.
- **Qualitative signals** — support tickets, feedback, and recordings of sessions that dropped at the broken stage when the tool provides them.
- **Flow cost** — if activation is the problem, compare the real path with the budget in `flow-audit.md`.

## Phase 5: Decide

Recommend one of:

- **Keep** — targets met. Remove the feature flag, make the code permanent, and choose what to keep monitoring (an alert on the guardrails).
- **Rework** — a specific stage is broken and a fix can be named. Say which skill to run next (`happy-path-audit`, `adoption-plan`, `usability-test-plan`…), what should change, and set a new review date. Allow one rework cycle; a second miss leads to a remove-or-keep decision, not a third attempt.
- **Remove** — the kill criterion is met and no fix is credible. Plan the removal: tell the users who rely on it, let them export their data, then delete the code, flags and events. Removing a feature that didn't work is the process succeeding, not failing.

Don't move the goalposts. If the team wants to change a target after seeing the data, record it as a changed target, with the reason, next to the original.

## Output

Add a `## Launch review — <date>` section to `brief.md` (or write `launch-review.md`): the promises-versus-actuals table, data caveats, diagnosis, decision, owners and dates, and the cleanup tasks. Open it with a five-line summary for stakeholders: the decision, the primary metric against its target, guardrails, confidence in the data, and the next step.
