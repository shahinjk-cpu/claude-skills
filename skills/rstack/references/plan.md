# Write, review and approve a large plan

Plan multi-area features, migrations, new subsystems and multi-day work. Give routine tasks and bug fixes a short spec.

## Read first

- The goal in the human's words and their prior decisions.
- The repo's `CLAUDE.md`, contributing guide, code, open PRs, CI and deploy state. Count PRs by author when checking the queue.
- Previous plans, their latest state sections and the ledger tail.

Check claims against code, logs or the human's words. Label them measured, inferred or guessed.

## Plan template

Give the human their list of asks plus a one-screen plan. Put the detail in appendices. Follow the [writing guide](writing.md#plans-and-reports).

```
# <Plan name>
Written <date>. <Human approvals already on record, if any.>

## What I need from you
<Only steps that need the human. Give the command or choice, when it is needed and what it holds. Say if there are none.>

## Plan
<One screen. State the goal, how to prove it, what starts now, the critical path and what could hold it.>

## Appendix A. Work items and evidence
<What is live, built but off or broken, with links.>
| ID | Item and files | Lane or owner | Size | Depends on | Done when |
|----|----------------|---------------|------|------------|-----------|

## Appendix B. Timeline, cost and risks
| Day | Lands and is switched on | Human steps | Gate |
|-----|--------------------------|-------------|------|
<Build and review time, CI and deploy waits, and cost by lane and total with a basis from this repo or current usage.>
<Risks, outside clocks, what each holds and what is out of scope.>
```

## Plan panel

Send the plan to two or three reviewers on different model families in parallel. The planner cannot sit on the panel. Give each the plan, repository and main SHA.

Ask about coverage, ownership of shared files, dependency order, time for build and review, CI and deploy windows, the human's steps, risks and accuracy. Ask each reviewer to write `PLAN-REVIEW-<model>.md` starting with `PLAN: GO` or `PLAN: FIX`, followed by ranked findings with work item IDs and fixes.

Combine the panel's P1s into one revision. Fix affected drafts before landing or applying them. Keep independent work moving. The conductor settles process questions and reports the rulings afterward. Put any remaining human-only steps in the ask list.

## Execute and update

- Start builders on reversible drafts as soon as their scope is clear. Start reviewers as drafts are ready, while the plan is still under review. If the human is unavailable today, present the framing once and run everything reversible. Hold only the [human-only steps](trust.md#human-steps-and-queue-decisions) that lack approval.
- Log any human approval with the date and exact words. Start independent work together. Schedule work later only for a dependency, a real outside clock or a capacity limit.
- Each day add a dated state section. Record landings, slips with causes, new findings and next steps. Mark timeline changes in place.
- Keep work within the requested scope. Record assumptions in reversible drafts. If the scope changes enough to need a new large plan, revise and review it while independent work continues.
- Close the plan when its success checks pass on the real path.
