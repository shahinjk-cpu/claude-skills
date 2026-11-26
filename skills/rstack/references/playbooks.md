# Playbooks

Use the steps for the work at hand as your task list.

## Review and fix

Give each part one [review by risk](reviews.md). Fix blocking findings inside the landing and let CI judge the fixes. Do not start another review round. For a P1 in security, money, auth, data integrity or a production incident, the same reviewer checks only the fix once. Hold the landing if it remains open.

## Bug fix

1. For a production bug, have a read-only investigator find the cause, the code path, affected dates and users, when it started and any siblings with the same fault.
2. Brief a fix for the cause and its siblings. Add a test that fails if the fix is reverted and a check for behaviour that must still work. Use a short spec for routine fixes.
3. Build, review by risk, pass CI, land and prove the fix on the real path.
4. If data needs repair, use a reviewed production write card with dry run, counts and undo.

## Feature

1. For large work, start builders and reviewers on drafts while the plan is under review. For a routine feature, start with the short spec. Name the switch, its default and how to turn it on or off.
2. Run independent layers in parallel and assign one integration owner. If the human is unavailable today, present the framing once and run everything reversible. Hold only the [human-only steps](trust.md#human-steps-and-queue-decisions) that lack approval.
3. Where the feature needs a switch, land it off and verify the deploy. Review the turn-on as its own step. Test the kill switch and exercise any restore path with a failed release.

## Investigation

Give the investigator a read-only identity and stop on a denied read. Ask for the cause, evidence, affected siblings, proposed fix and owner. If a small prototype can settle a design question, run it.

## Figure it out

When no playbook fits, design the workflow before anyone writes code. Follow [Figure it out](figure-it-out.md).

## Queue check

1. List all open PRs and count them by author every time. Record author, lane, readiness and blockers. Give every author's work a lane, including work outside the current plan. This exposes ready work that otherwise gets overlooked.
2. Check base, head and CI for each landing. Prefer the reviewed PR itself and use the repo's merge path. Keep ready contributor work moving while the conductor's critical work builds. Keep a short reason for any hold.
3. Apply the train CI cap and cancel superseded runs so the work that can land next gets a runner. Check the newest deploy and the freeze. Record the ruling and report it in one line. Follow the [merge queue](merge-queue.md).

## Shipping a train

Combine parts only when they need to land together and branch protection and required approvals still hold. Fold them in dependency order. Check patch IDs and regenerate outputs. Run the [push gate](merge-queue.md#push-gate) before every push or ready toggle. Read a red CI run in full and fix all its failures in one push. Write a cause file before any rerun. Land one exact-base train, verify its deploy and report the new base. Run deciding CI on the next exact landing tree.

## Restart or hand over

1. Read the newest handoff, the ledger tail and the latest plan state.
2. Count open PRs by author, check CI by head SHA and list running agents. Verify work recorded as done.
3. Re-arm background CI waiters. Batch orders and leave lane windows idle while background agents run. Have them report on events. Each message wakes the window and uses context.

## Wind down

Start nothing new. Save work on `wip/` branches, let running agents finish and update handoffs. Land green work that clears the gates and freeze. Write the main conductor's handoff last.

## Turn repeated instructions into checks

When the same rule appears in three briefs, put it in a script, test, lint rule or config value. Point new briefs to it.
