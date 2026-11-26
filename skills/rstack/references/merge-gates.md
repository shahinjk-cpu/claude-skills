# Merge gates and the landing queue

Use [merge queue](merge-queue.md) to order landings and run the push and merge gates.

## Assembling a train

1. Use the repo's merge path. Prefer the reviewed PR itself. Pick related parts within the landing caps only when they need to land together and the combined PR can meet all protections and approvals. Check each part's single verdict or diff read and any required item outcome.
2. Cherry-pick in dependency order onto main or the single allowed stack base. Compare each part's patch IDs with the reviewed commits and record any fixes cleared under the P1 rules.
3. Drop obsolete regeneration commits. Take the base's generated files and regenerate once on the final tree. Check every changed row against the reviewed parts. Resolve behaviour conflicts with the owners and run both features' tests. See [coordination](coordination.md).
4. Put each part, verdict and CI evidence in the PR body. Run the [push gate](merge-queue.md#push-gate) before every push or ready toggle. Use shared local slots for heavy runs. Leave the full suite to CI.

Fix P1s inside the landing and let CI judge the fixes. Do not start another review round. For a P1 in security, money, auth, data integrity or a production incident, the same reviewer checks only the fix once. Hold the landing if it remains open. See [reviews](reviews.md#when-a-fix-needs-another-read).

## CI and reruns

Read CI by head SHA and workflow. Check names can collide across workflows and skipped jobs.

```sh
gh api --paginate "repos/<owner>/<repo>/actions/runs?head_sha=<sha40>&per_page=100" \
  --jq '.workflow_runs[] | [.id, .path, .event, .run_attempt, .status, .conclusion] | @tsv'
```

- Match each required workflow to the run for the tested candidate and check its latest attempt. A skip counts only where repository policy allows it. Run long waits in the background and report when a run changes state.
- With shared runners, cap trains in CI at `caps.trains_in_ci` (two in the example). Cancel runs for superseded heads before replacing them. Give scarce slots to the work that can land next and to deadline fixes.
- Read the entire red run before fixing it. Collect every failure and fix them in one push. Run the push gate on that head.
- Before any rerun, save a cause file with the failed assertion, run and head, evidence, and proposed action. The main conductor authorizes a rerun based on that file. See the [cause reader brief](briefs.md).
- Investigate intermittent money, auth or data failures as possible real bugs. An intermittent billing failure once exposed a real ordering bug. A passing retry would have hidden it. Prove the cause before deciding whether to fix and run CI on a new head or rerun the same one.
- For a supported test or runner flake, authorize one rerun on the same head. If it fails again, stop and fix or escalate the cause. Attach the cause file to every green result from a rerun.

## Landing order and exact base

- Pick a ready PR or train whose CI passed on its exact landing tree. Keep contributors' ready work moving. Hard deadlines can jump the queue. Record why.
- Record the PR head, the current main SHA used as base and the tree SHA that CI tested. The deciding CI must cover the tree that will result from this merge. A green branch on an old base or on a stack is early signal only.
- Land one PR or train at a time through the repo's merge path. Keep all required checks and approvals in force. Confirm human authorization for protected branches. Use a protected queue that checks the base at merge time, or serialize all writes to main and recheck the base and head immediately before merging. Stop if either moved or if the landing method changes the tested tree.
- Tell every lane the new main SHA after a landing. Prepare the next landing and run deciding CI on its exact tree. Compare trees before carrying a local gate result. See [merge queue](merge-queue.md).
- Assign migration and contract version numbers in landing order. Keep provisional numbers in the migration and its test so renumbering is mechanical. If renumbering changes the candidate tree, test that tree before merging.

## Deploy and restore

- Check the deploy freeze and any human task a deploy would interrupt. Merge only if the deploy can finish before the freeze starts. Use recent deploy times plus a margin. If completion is uncertain, hold the train and resume after the freeze.
- Check that the newest main deploy succeeded. Use a one-deploy exception only when the ruling names the failed run and attempt. Retire a freeze only with deploy survival evidence and a recorded ruling.
- Record the ruling, PR, head, base, tested tree, CI runs, migrations, infrastructure changes and deploys in flight. Use the protected queue if the repo has one. If the repo allows a direct merge, pin the head at merge. See [merge when green](merge-queue.md#merge-when-green).

- Walk the deploy. Check the run, the health or version endpoint, alarms and the promised user path. Record the evidence.
- For release changes that depend on a restore or rollback path, run a test that fails a release and performs the restore. Check the prior version, health and data before calling it safe. A code read cannot show that the restore works.

## Gates on infrastructure plans

Refuse risky permission and secret changes by default. Use narrow, named flags and test both refusal and allowance. The human applies privileged plans from a script that checks the exact plan line and changed addresses, then asks for a typed `apply`.
