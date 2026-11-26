# Worked example. Team billing

This run is fictional. Its timings and costs belong to the example. A subscription app has personal billing and shared workspaces. The goal is to let a workspace owner start seat billing, add seats and see the next invoice.

Success means an owner sees the right seat count and amount. A member cannot change billing. Duplicate or late events cannot change the bill twice or restore an old count. Personal billing still works.

This is large work. It touches the billing service, schema, settings page and release process. The lanes can build in parallel, but they cannot all ship together.

## Day 1. Plan and drafts

The planner uses the Frontier model `fable`. It reads `billing/personal.py`, `teams/roles.py`, the deployment record and open PRs. The measured baseline is one personal billing path and no workspace invoice path. The plan lives in `plan/team-billing.md`.

| Item | Owner | Size | Needs | Done when |
|---|---|---|---|---|
| B | Billing | 1 day | None | Seat records drive the next invoice. Retries and member access are covered. |
| U | Portal | 1 day | B's API contract | An owner sees the next invoice and a member gets a refusal. |
| R | Release | Half day | B and U on main | A release failure can be restored and the pilot can be switched off. |
| D | Docs | 1 hour | Agreed wording | The setup guide explains who can manage seats. |

The critical path is B's schema and invoice logic, U's real settings flow, R's failed-release test, then the pilot. D can land on its own. Plan for 40 minutes per whole-suite CI run and up to 25 minutes per deploy based on recent runs. The agent cost estimate is $58. That is $14 for planning and panel, $23 for billing, $11 for portal, $8 for release and $2 for docs. These are estimates from similar part logs.

| Day | Work and gates | Human steps |
|---|---|---|
| 1 | Pin a draft API contract and start lanes during the plan review. Land docs when approved. Leave time for the nightly freeze. | Authorize the planned protected-branch merges and choose when seat changes take effect. |
| 2 | Land billing and portal dark. Pass the failed-release drill in staging. | None. |
| 3 | Land release checks and verify a pilot workspace. | Approve and run the pilot switch. |

The human chooses `next-cycle` (recommended) over `immediate`. In this run, refunds, credits and moving existing subscriptions are out of scope.

The two panel seats ran in parallel. Neither wrote the plan.

```text
plan/PLAN-REVIEW-opus.md
PLAN: GO
Portal can build against the pinned API contract while billing runs its tests.

plan/PLAN-REVIEW-astra.md
PLAN: FIX
P1 R. A flag-off check leaves the migration restore untested. Fail a staging release and restore its prior version and data.
P1 Timeline. Put the 22:00 to 06:00 UTC deploy freeze on the schedule.
```

The lanes started drafting while the panel ran. The conductor added the failed-release drill to R's draft and allowed for a Day 2 landing if CI finished too late on Day 1. The human replied `Approved to merge the listed PRs when ready. next-cycle.` The conductor recorded the date and those words in `plan/ledger.tsv` before any merge.

## Windows, files and models

The main conductor owns the ledger, scope decisions and merges. Four windows act as sub-conductors. The map in `plan/owners.md` gives each shared file one owner. The windows batch questions and next steps. They stay idle while their agents run and report at events.

| Window | Files it owns |
|---|---|
| Billing | `billing/`, `db/migrations/`, `tests/billing/` and the shared API contract in `api/billing.schema.json` |
| Portal | `web/settings/billing/` and `tests/web/` |
| Release | `release/`, `tests/release/` and the shared flag registry |
| Docs | `docs/team-billing.md` and `docs/settings.md` |

| Part | Grade | Chosen model | Scope |
|---|---|---|---|
| B1 | Hard | `opus` | Seat ledger and migration |
| B2 | Hard | `opus` | Seat event processing and invoice totals |
| U1 | Hard | `opus` | Owner-only route and member refusal |
| U2 | Normal | `sonnet` | Invoice preview and empty state |
| R1 | Hard | `opus` | Fail a release and restore the prior version |
| R2 | Hard | `opus` | Pilot switch and rollback smoke test |
| D1 | Easy | `opencode/deepseek-v4.1-flash-free` | Write an exact three-step setup guide |
| D2 | Easy | Human contribution, no model | Fix the existing settings link in PR #81 |

The Docs window added D2 to its lane at the first queue check and agreed with its author to add D1 to #81. The cheap model edited only `docs/team-billing.md` in a guarded worktree. The Docs window read the diff and ran the link check.

> Docs D1 built. One file. Link check passed. No agent review required.

The Billing window gave its strong B2 builder `billing/seats.py`, `api/billing.schema.json` and `tests/billing/test_seats.py`. The builder used a unique event key and tested a duplicate delivery. It kept changes out of `billing/personal.py` and opened a draft.

> Billing B2 draft ready. Head `82b0201`. Six focused tests passed. Review brief sent.

## Review the money path

The B2 reviewer used `gpt-6.2-astra`, a different model family from the builder. It got the spec and the B1 and B2 candidate. It checked the complete billing path and tried duplicate and out-of-order events.

```text
reviews/B2.md
VERDICT: FIX
Head: 82b0201
The next-cycle total, duplicate event case and personal billing inverse match the spec.
P1 billing/seats.py:118. Replay distinct events at revisions 12 then 11. The owner sees 3 seats after revision 12 set 5. Expected 5.
```

The plan had covered repeat delivery of the same event. It had missed an older event arriving late with a different ID. The lane reproduced the fault through the invoice preview and sent the choice to the conductor. The conductor ruled to apply only revisions newer than the last one written, in the same transaction as the seat update. The lane added tests for out-of-order and later valid events.

```text
reviews/B2-fix.md
VERDICT: PASS
Head: 82b0202
Focused fix check. Replay 12, 11, 13. Invoice seats are 5, 5, 6.
```

The same reviewer checked only the money fix once. Its earlier review covered the complete B1 and B2 candidate, so it also covered item B. The PR recorded both verdicts and still needed green CI.

U2's combined review was routine:

```text
reviews/U2.md
VERDICT: FIX
Head: 83b0201
P1 web/settings/billing/preview.ts:44. The empty state renders a blank label while the request loads.
```

The Portal builder fixed the label and added a pending-state test and a loaded-state test. The lane recorded the new head. CI judged the fix. B1, U1, R1 and R2 got their required part reviews. The Portal and Release item outcomes checked the full paths.

## Fold, test and land

Docs kept the teammate's original #81 and checked both changes in the settings help path. Billing folded B1 and B2 into #82 so seat records and invoice logic would ship together. Portal folded U1 and U2 into #83. Release prepared R1 and R2 for #84. The lanes compared patch IDs, recorded the P1 fixes and regenerated shared outputs on their folded trees. Every PR kept the repo's required checks and approvals.

Before first CI, Billing ran the previously failing `tests/billing/test_event_order.py`, the changed `tests/billing/test_seats.py` and the cross-cutting files:

- Seam and invariants in `tests/invariants/test_checkout.py`.
- Snapshot in `tests/snapshots/test_api_census.py`.
- Schema rules in `tests/schema/test_migrations.py`.
- Sandbox in `tests/sandbox/test_billing.py`.

Each Billing part had passed alone. The census failed on the folded tree because it lacked an invoice field already covered by B2's review. The train owner regenerated the census, checked the changed row against B2 and ran the preflight again. The whole suite ran in CI.

- **19:10 UTC queue check.** Contributor 1 (#81), Billing 1 (#82), Portal 1 (#83), Release 1 (#84). #81 is ready for deciding CI. #83 starts early CI on its stack. Both slots are in use with #81's deciding CI.
- **19:35 UTC.** #81 lands first while billing is still building. Its CI tested the exact landing tree. The deploy passes. Main tells all lanes to use base `a1000d1`. Main cancels #83's early run on the superseded stack and gives #82 a slot.
- **21:20 UTC.** #82's CI run 2407 fails in `tests/sandbox/test_clock.py:31`. A reader checks the same fixture on main and finds that it reads wall time while the runner resyncs its clock. There are no failures in the changed billing path.

```text
causes/2407.md
CAUSE: B runner clock step
Head: 82c0021. Run 2407 runner log records a clock step during the fixture.
The time assertion and fixture match main. Run 2399 shows the same failure on main.
Recommend one rerun on 82c0021. Release lane owns replacing the wall clock in the test.
```

> Billing #82 green. Base `a1000d1`, head `82c0021`, tree `b173ac0`. Run 2407 attempt 2 passed after one authorized rerun. Cause file attached.

- **21:42 UTC queue check.** Billing 1, Portal 1, Release 1. Freeze starts at 22:00 UTC. A deploy can take 25 minutes plus a 10-minute margin. The conductor holds #82.
- **Day 2, 06:05 UTC.** The freeze is over. Base, head and tested tree still match. The conductor lands #82 and verifies the dark deploy. The new base is `a2000d2`. Portal rebases once onto it, retargets to main and reruns CI. Release updates its stack and waits for a slot.
- **Day 2, 07:35 UTC.** #83 lands on the exact tree tested after its rebase. CI passed the U2 pending and loaded cases. Main announces `a3000d2`. Release rebases once onto it and runs deciding CI.
- **Day 3.** #84 clears the staging drill. The drill injects a failed release health check, restores the prior version, then reads the seat count and personal invoice again. Both match the pre-release values.

## Merge queue

On #84's first ready run, the required baseline check for an advisory scanner went red. The conductor read the full run and found one stale baseline. The trial scanner workflow itself was advisory. The conductor regenerated the baseline, checked the reviewed entries and added the CI-pinned baseline command to the push gate for changes to its inputs. The conductor cleared the fix under the review policy and ran the extended gate before pushing once and again before each ready toggle. The ruling recorded green CI for the new head and the successful deploy on main. The conductor merged #84.

> Release #84 verified. The failed-release drill restored version and data. Pilot remains off. Evidence in `release/restore-drill.md`.

The human approved the reviewed pilot card and ran `./release/pilot.sh enable --workspace pilot`. Its dry run expected one workspace. The after-read returned one enabled workspace. The undo command in the card was `./release/pilot.sh disable --workspace pilot`. The conductor verified the version and alarms, then watched an owner start billing and add seats. It ran the member, duplicate, late-event and personal billing checks. All five passed on the pilot path.

## Daily summary, audit and reflect

The conductor checked PRs, CI and deploy logs before writing the Day 2 state in the plan.

> Measured. #82 and #83 landed and both deploys verified. Billing slipped from Day 1 because of the freeze. The pilot is off. Release owns #84 and the clock-test follow-up. The human has no step today. The pilot switch is due Day 3.

The auditor used a different model family and wrote `audits/day-2-readiness.md`:

```text
AUDIT: FINDINGS 1
P2 release/alerts.yml:38. The invoice delay warning has no assigned owner. Evidence: staging alert test 67.
```

The conductor added A1 to the living plan with Release as owner, a Day 4 due date and a check that a test alert reaches the release queue. It stays visible as a follow-up to the pilot.

Reflect at the Day 2 handoff. B2's late-event defect escaped the initial plan. The conductor added `tests/billing/test_event_order.py` to the push gate's test families. The release lane ran the gate on #84 and recorded the pass in the ledger.
