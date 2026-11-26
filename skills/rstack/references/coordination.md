# Coordinating lanes before and during a merge

## Own the files

- Read the repo's `CLAUDE.md`, contributing guide and CI checks before assigning files or writing generic rules. For file moves, run the affected checks, including sandbox and allowlist checks where the repo has them. Check workflow and container changes used by jobs on self-hosted runners.
- Each plan item lists its files and areas. The plan panel checks for two parallel edits without a single owner. The conductor keeps the map in `plan/`.
- Shared routers, schemas, flag registries and configs get one owner at a time. If a lane needs a file outside its area, the conductor sequences the edits or assigns the change to the owner.
- At each queue check, count open PRs by author and assign every author's work to a lane with an owner. The lane may already exist. A contributor's ready work must never wait behind the conductor's unfinished critical path. See the [queue playbook](playbooks.md).

## Sequence and stack

- Check base branches and commit ancestry. Several PRs from one author may already be a stack. Keep the original PRs and land them in dependency order where the repo allows it. Draft dependent parts on that stack or against an agreed interface.
- Combine parts only when they need to land together and the resulting PR can meet the repo's protections and approvals. When staging a new landing, stack only the next one. Use stacked CI for early signal. Follow the repo's rebase or retarget flow and run deciding CI on the next exact landing tree. See [merge queue](merge-queue.md).

## Share files without overwriting work

- Builders use their own worktrees. Keep stash, reset and checkout out of checkouts other sessions share.
- Keep the head steady while a review or deciding CI is running. If CI is obsolete, cancel it before pushing the replacement head. Record which head each verdict or run covers.
- Builders run checks that show which generated rows their change affects. The train owner takes the base's generated files, drops obsolete regeneration commits and regenerates once on the final tree. Check that the reviewed rows carry through.
- Claim migration and version numbers provisionally. Set them in landing order under the [merge gates](merge-gates.md).

## Land in order

The main conductor lands one PR or train at a time through the repo's merge path and announces the new main SHA. Prepare the next landing on that base within the CI cap. Check patch IDs to carry reviews forward after a pure rebase.

## Resolve conflicts between features

1. Stop when a conflict touches two reviewed features. Have the owner of each agree on the merged behaviour. They each know what their feature must preserve.
2. The owner of the conflicting file records the agreed resolution in a named integration commit. Send design trade-offs to the main conductor.
3. Keep the earlier verdicts with the landing evidence. Run both features' tests and let CI judge the resolution. Apply the [P1 fix rule](reviews.md#when-a-fix-needs-another-read) if the resolution fixes a blocking finding.
4. Log the decision. If the same areas keep colliding, fix the ownership map or sequence.
