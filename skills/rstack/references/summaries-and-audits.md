# Summaries and regular audits

Many agents produce a lot of change fast. Summaries keep the human oriented; audits catch what the day-to-day loop misses: drift, slow regressions, findings nobody owns, and a plan that no longer matches reality.

## Summaries

### When
- **Daily state** (end of each working day, or each morning): a dated "state on <date>" section in the plan.
- **On request** ("what got done overnight", "where do we stand"): a summary built from the record, not from memory.
- **At every milestone**: a train landed, a plan phase done, a production step finished.
- **Before a handover** (usage limit, restart): the conductor's handoff file doubles as the summary.

### What a summary contains
1. **Landed and live**: what merged and is verified in production, with counts (PRs, commits, deploys) taken from git and CI, not estimated.
2. **Against the plan**: ahead, on time, behind, per area, and why for each slip (with the outside clock if there is one).
3. **Found**: new defects or risks, ranked, each with an owner and a date.
4. **In flight**: what is building, in review, in CI, and when it is expected.
5. **Needs the human**: one current list of their steps and one-word decisions, each with the exact command or the recommended answer.

### Rules
- Every number and status is checked against git, CI, deploy logs or the ledger before it is written, and labelled measured, inferred or guessed. A wrong summary costs more trust than a late one.
- Lead with what changed for the human, in plain words; put detail in links (PRs, verdict files, the plan).
- Long summaries go in a document (the plan, a doc or a page) with a short message pointing to it.

## Regular audits

An audit is a read-only pass by an agent that did not do the work (the `auditor` agent, ideally on a different model family), producing ranked findings that go back into the plan. The human can set a different cadence in the plan.

| Audit | Cadence | What it checks |
|---|---|---|
| **Plan vs reality** | daily, with the summary | every work item's real state against the plan; slips, silent scope growth, items marked done without evidence |
| **Findings ledger** | every 2 to 3 days | every P1/P2/P3 from reviews and investigations has an owner and a date; nothing is quietly dropped; repeated finding classes have become checks |
| **Production readiness** | weekly, and before any launch | security (auth, permissions, secrets, dependency advisories), reliability (alarms, kill switches, restore drills), performance (load, limits), data correctness, the features promised |
| **Drift** | weekly | infrastructure versus its code (a refresh-only plan), alarms that never fire or always fire, flags left half on, permissions wider than needed |
| **Hygiene** | weekly | stale branches and worktrees, open PRs with no owner, flaky tests (fixed at the cause, not retried), disk and memory pressure on the build machines |
| **Cost and usage** | weekly | model usage per role, CI minutes, cloud spend against budget; where to move work to a cheaper model or cut a loop |

### How an audit runs
1. The conductor briefs the auditor: scope, the record to read (plan, ledger, verdict files, git, CI, deploy logs, read-only production reads), the identity to use (least privilege; a denied read is a stop and a reported gap).
2. The auditor writes `audits/<date>-<kind>.md`: line 1 `AUDIT: CLEAN` or `AUDIT: FINDINGS <n>`, then findings ranked P1/P2/P3, each with evidence and a proposed owner.
3. The conductor turns each finding into a plan work item with an owner and a date, or a one-word decision for the human, and notes it in the summary. For work without a plan, record the finding as an owned follow-up with a date. State when an audit is clean.
