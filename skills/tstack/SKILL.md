---
name: tstack
description: Master orchestrator and suite guide for Theo Browne's (t3dotgg) tstack agent skills. Covers PR workflows, autonomous shipping, multi-model review council, and PR maintenance (full-send, full-stop, council, sol-loop, file-pr, takeover, babysit-pr, modernize, leaving-pr-comments). Use when the user mentions tstack, PR automation suite, or wants guidance on which tstack skill to run.
metadata:
  version: 1.0.0
---

# tstack: Theo Browne's Daily Agent Skills Suite

`tstack` is an opinionated suite of GitHub and PR workflow skills designed by Theo Browne (t3dotgg) for autonomous, verified software development in Claude Code, Codex, Cursor, and agent environments.

## The 9 tstack Skills

| Skill | Trigger / Say | What it does |
|---|---|---|
| `full-send` | "full send" | Takes a change completely to a merged PR without manual intervention: proves it, reviews it, files it, babysits it through CI, and merges it. |
| `full-stop` | "full stop" | Same autonomous pipeline as `full-send`, but pauses right when the PR is verified and ready for you to manually merge. |
| `council` | "council" | Cross-model review panel: gets review from three different models/providers and loops until they achieve consensus. |
| `sol-loop` | "sol loop" | Reviews a change with GPT Sol in a loop until both agents agree. |
| `file-pr` | "file a PR" | Files a concise, issue-led pull request that explains the problem and verification rather than an inventory list. |
| `takeover` | "take over" | Adopts and finishes someone else's PR, branch, or agent thread, rebases it, and preserves their original credit. |
| `babysit-pr` | "babysit" | Continuously monitors a PR through CI and review bots, auto-fixing real test failures or linter issues. |
| `modernize` | "modernize" | Rebases an old, stale PR against the target branch and evaluates whether it should still exist or be closed. |
| `leaving-pr-comments` | (automatic) | High-fidelity formatting guidelines for comments and review notes posted by agents on GitHub. |

## Skill Dependency Graph

- `full-send` -> calls `sol-loop`, `file-pr`, and `babysit-pr`.
- `full-stop` -> calls `full-send` with stop flag before merge.
- `takeover` -> calls `modernize`, `file-pr`, `babysit-pr`, and `leaving-pr-comments`.
- `file-pr`, `babysit-pr`, and `modernize` -> call `leaving-pr-comments`.

## Usage Guidelines

When you want to run one of these workflows:
1. For end-to-end autonomous shipping: invoke `/full-send` or `/full-stop`.
2. For high-stakes code review: invoke `/council` or `/sol-loop`.
3. For managing PR lifecycle: invoke `/file-pr`, `/babysit-pr`, `/modernize`, or `/takeover`.
