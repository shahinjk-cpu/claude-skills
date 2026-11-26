# Merge queue

## Landings

- Read the repo's `CLAUDE.md`, contributing guide, CI checks, merge settings and deploy rules first. Use its normal merge method or protected queue. Check the PR bases and dependencies before grouping work.
- Prefer landing a teammate's reviewed PR itself. Open a separate landing PR only when changes need to land together and the new PR can meet every branch protection and required approval. Never recommend or use weaker branch protection or fewer approvals. If an approval is unavailable, hold that landing and keep other work moving.
- Land one PR or train at a time. When combining, count commits and source PRs before folding. Use the repo's limits or the configured `caps.commits_per_train` and `caps.prs_per_train` if it has none. The example uses 40 commits and 6 PRs.
- Fix P1s inside the landing. Carry reviews when the patches still match and record fixes cleared under the [review policy](reviews.md). Write a ruling for the final head, base and tested tree.
- Preserve contributor stacks and land them in order. When staging a new landing, stack only the next one. After the current PR lands, rebase and retarget the next PR if the repo's merge path calls for it. A host rebase merge rewrites SHAs. Require deciding CI for the exact landing tree even if it matches the stacked candidate.
- Drop the old regeneration commit when rebasing. Take the new base's generated files and regenerate once on the final tree. Carry the reviewed rows and check the regenerated diff against them. Leave generated conflicts to the generator.
- Compare the new main tree to the old stack base tree, the head the next landing was stacked on. If they match, a pure rebase yields the same candidate tree. Confirm both candidate tree SHAs match. Carry the prior gate result as evidence for checks whose inputs still match. Clear the push gate on the rebased head so the history, range and PR body checks see the new inputs. Require fresh CI on the new head.
- Drafts may skip heavy CI. Check when the repo starts CI. If it requires a ready event after a push, follow that flow. Run the push gate before each push or ready toggle.
- Read a red run in full before starting a fix. Fix every red in that run in one push. Write a [cause file](briefs.md#cause-reader-brief-before-any-rerun-or-fix) before any rerun. Record what failed, why and whether the same head should run again.
- Keep a freeze until the work it protects survives a deploy. Record the job ID, the deploy that interrupted it, and evidence that the same job resumed and completed. Record the retirement as a ruling and update the configured windows.

## Push gate

Run the repo's pre-push checks before any push or ready toggle. Include checks from its instructions and CI that cover the changed files. Use the [push gate helper](../scripts/push-gate.sh) when it fits the repo. Use a clean candidate checkout and a base that is an ancestor of its head. Keep the worktree fixed during the run. The script runs from a frozen copy of itself.

```sh
bash <skill-dir>/scripts/push-gate.sh <worktree> <pr-number-or-body-file> <base-ref> [config-file]
```

Use the local PR body file before the first push. Use the PR number to fetch the current body after it exists. Resolve explicit file arguments from the caller's directory. The default config lives in the worktree as `conductor.config.json`. Use Bash, Git, `jq` and `gh` for GitHub PR reads.

1. Check the PR description. Scan the commit range for secrets. Run the repository's history or section walk. Refuse any commit with the same tree as its first parent. A rebase can drop a change and leave an empty commit.
2. Run the test families that have broken trains. Include earlier failures and changed test files. Set a minimum for each configured family so a bad glob cannot silently select nothing.
3. Run every test that names a changed non-test file by literal path. Also run tests named for a changed module. Leave general import matching to CI. One widely imported module can otherwise select the whole suite.
4. Run CI's other blocking suites locally when their inputs change. Include data-read suites and security scanners such as Checkov at the CI-pinned version. Use the same commands as CI. Record the result before pushing or toggling ready.

## Merge when green

Use the repo's merge path first. If it permits direct rebase merges, [merge when green](../scripts/merge-when-green.sh) can watch a landing from the project root. It uses Bash, `jq` and `gh` with pagination and `--slurp` support. Pass the final head SHA and the ruling file. A direct merge pins the PR head but cannot pin main atomically. Use a protected host queue if another writer can race the merge. Keep all required checks and approvals in force and use a credential that cannot bypass them. Confirm human authorization before merging to a protected branch.

```sh
bash <skill-dir>/scripts/merge-when-green.sh <pr-number> <reviewed-head-sha> <ruling-file> [config-file]
```

1. Require the ruling file and the reviewed PR head. Check that the PR targets main. Use the compare API to confirm main is an ancestor of the reviewed head. Recheck the base before merging.
2. Read all workflow runs for the head. Use the latest attempt of the newest run for each workflow. Require at least the configured number of workflows and a completed `success` or `skipped` result for each. Set the floor for the repository's expected workflows. Keep individual required checks in branch protection. Exclude advisory workflows, such as a trial shadow runner, by exact file path only.
3. Require the newest main deploy to be completed and successful. To fix a single failed deploy, name the run and attempt in the ruling on its own line as `ALLOW_RED_DEPLOY=<run-id>:<attempt>`. State why this landing fixes that deploy. The exception expires when a newer run or attempt appears.
4. Hold while a configured freeze is open or the deploy may run into one. Set the buffer from recent deploy times plus a margin. Log each loop. Retry unreadable reads. Exit on the first red and hand the run to the cause reader.
5. Merge one linear landing with the reviewed head pinned. Verify the deploy and real user path. Close any folded source PRs whose work landed and report the ruling in one line. Replace a running helper atomically. Write the replacement to a new file in the same directory and rename it over the old file.

## Config keys

Copy [the example](../conductor.config.example.json) to `conductor.config.json`. Fill in the project values. Use trusted config. Command arrays contain a program followed by its arguments. Each command runs from the worktree root. Use a wrapper when a command needs shell logic or CI tool setup.

| Key | Set it to |
|---|---|
| `caps.commits_per_train`, `caps.prs_per_train` | Max commits and source PRs per landing. Defaults are 40 and 6. |
| `autonomy.proceed_without_asking` | Include `queue_rulings` and other reversible queue work within scope. |
| `autonomy.pause_for` | Use the human steps in [trust and access](trust.md#human-steps-and-queue-decisions). |
| `merge_queue.repository`, `merge_queue.main_branch` | GitHub `owner/repo` and the landing branch name. |

Set these keys under `merge_queue.push_gate`.

| Key | Set it to |
|---|---|
| `pr_description_command` | Command that checks the body file at `CONDUCTOR_PR_BODY`. |
| `secret_scan_command` | Secret scan for `CONDUCTOR_RANGE`. Use the CI rules and redact findings. |
| `history_walk_command` | Repository history or section walk. Use `[]` when the repository has none. |
| `test_command` | Test runner argv. The gate appends selected paths as individual arguments prefixed with `./`. |
| `test_paths` | Globs for tracked files that qualify as tests. |
| `test_families[].name`, `.paths`, `.min_files` | Family label, test path globs and positive file floor for that family. Add known prior failures here. |
| `reader_path_prefixes` | Optional directory prefixes to strip from changed paths when looking for literal reads in tests. Use trailing slashes. |
| `module_test_names` | Test filename globs with one `{module}` placeholder for the changed file's basename stem. |
| `blocking_suites[].name`, `.inputs`, `.command` | Suite label, changed path globs and exact CI command. Include the workflow and baseline files in the input globs. |

Path globs match whole repository-relative paths. `*` can span directories. Commands also receive `CONDUCTOR_WORKTREE`, `CONDUCTOR_BASE`, `CONDUCTOR_HEAD`, `CONDUCTOR_RANGE` and `CONDUCTOR_COMMIT_COUNT`. Base and head are pinned commit IDs. The range is `base..head`.

Set these keys under `merge_queue.merge_when_green`.

| Key | Set it to |
|---|---|
| `min_workflows` | Positive minimum number of workflows after advisory paths are excluded. |
| `advisory_workflow_paths` | Exact repository-relative workflow paths. Use `[]` to include every workflow. |
| `deploy_workflow` | GitHub Actions workflow ID or filename for deploys from main. |
| `freeze_windows` | UTC windows or `[]`. Each entry has `days` (ISO weekdays 1 for Monday through 7 for Sunday), `start_utc` and `end_utc` (`HH:MM`). An end before the start falls on the next day. The end is exclusive. |
| `deploy_lead_minutes` | Minutes of lead time before a freeze. Use zero to check only open windows. |
| `poll_seconds` | Positive delay between reads. |
| `log_file` | Path to the append-only queue log. Resolve relative paths from the project root. |

The merge helper returns 0 on merge, 2 on a ruling, config or invocation error, 3 on red, 4 on a changed or closed PR, 5 when main needs a rebase, and 1 when the merge request fails. Check PR state after an ambiguous merge response before starting the helper again.
