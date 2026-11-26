# rstack

rstack is a Claude Code skill for running several agents on one software project. The main conductor owns decisions and merges. Each lane runs its own builds and reviews. Route parts to models by difficulty and give reviewers a separate brief.

See the skill from plan to deploy in [the worked team billing example](references/example-run.md).

## Install

Copy this repository to `~/.claude/skills/rstack`. Then install its agent definitions.

```sh
mkdir -p ~/.claude/agents
cp ~/.claude/skills/rstack/agents/*.md ~/.claude/agents/
```

Use [the example config](conductor.config.example.json) as a starting point. Save your copy as `conductor.config.json` in the project root or `~/.claude/conductor.config.json` for user defaults. Use the model IDs your setup offers. For optional CLI and API setup, see [adapters](references/adapters.md).

## Use

Ask Claude Code to act as the conductor for a project. Give it a goal, such as adding team billing, or a short task, such as updating the setup guide. For large work, an independent panel reviews the plan while builders and reviewers work on drafts. Routine tasks and bug fixes start with a short spec.

With cross-window messaging, each lane can run in its own window. In one window the conductor runs the lane agents directly. The conductor uses the repo's merge path and verifies the deploy. See [human-only steps](references/trust.md#human-steps-and-queue-decisions).

## Configuration

| Key | What it controls |
|---|---|
| `roles` | Default tool and model per role. Pick two or three eligible model families from `plan_panel`. |
| `difficulty_grades` | Ordered model choices for Frontier, Hard, Normal and Easy work. |
| `review_policy` | Reviews by risk and scope, and the limit on critical fix re-reads. |
| `metrics` | Part log path, routing review cadence and when to move work to a cheaper model. |
| `trust_tiers` | Reference for access by agent tier. |
| `hierarchy` | Main conductor, lane windows and maximum depth. |
| `caps` | Limits on agents, local test runs, commits and PRs per landing, and trains in CI. |
| `merge_queue` | GitHub repository and base branch, local push checks, workflow and deploy checks, freeze windows and polling. See [merge queue](references/merge-queue.md). |
| `planning` | Which work needs a plan and which goes straight to a short spec. |
| `fallbacks` | Next eligible models when a route is unavailable. |
| `autonomy` | Reversible steps agents can take and actions that need a pause. |

The conductor follows these settings when it assigns work and gates merges. Set tool permissions separately. See [trust and access](references/trust.md).

## Repository files

- [SKILL.md](SKILL.md) has the core rules and links to every file in `references/`.
- [conductor.config.example.json](conductor.config.example.json) has the default settings.
- [agents/planner.md](agents/planner.md) writes large plans.
- [agents/plan-reviewer.md](agents/plan-reviewer.md) reviews large plans while draft work proceeds.
- [agents/builder.md](agents/builder.md) builds one part and opens a draft PR.
- [agents/reviewer.md](agents/reviewer.md) checks the spec or the outcome and writes a verdict.
- [agents/auditor.md](agents/auditor.md) checks project records and reports findings.
- [agents/codex.md](agents/codex.md) runs a build or review through the Codex CLI.
- [agents/opencode.md](agents/opencode.md) sends easy work through the guarded launcher.
- [agents/openrouter.md](agents/openrouter.md) sends read-only work with named files over the API.
- [scripts/oc-build.sh](scripts/oc-build.sh) prepares a worktree run and applies the guard.
- [scripts/opencode-guard.json](scripts/opencode-guard.json) lists paths and commands the guard denies.
- [scripts/openrouter-ask.py](scripts/openrouter-ask.py) sends one brief with named files.
- [scripts/openrouter-batch.py](scripts/openrouter-batch.py) runs a prompt over many items with a spend threshold and resume support.
- [scripts/route-stats.py](scripts/route-stats.py) summarises per-part metrics by task type and model.
- [scripts/run-slot.sh](scripts/run-slot.sh) limits heavy local runs across windows.
- [scripts/push-gate.sh](scripts/push-gate.sh) checks a candidate from a frozen copy before pushes and ready toggles.
- [scripts/merge-when-green.sh](scripts/merge-when-green.sh) watches one ruled landing and merges when its gates clear.

Python can create local bytecode caches in `scripts/__pycache__/`.

## Tests for the skill

`evals/` holds three real-task test cases (landing a day of PRs, an infrastructure migration while the human is away, and coordinating sub-conductor windows), each with a prompt, the expected outcome and one grader per checkable behaviour. Run them with and without the skill and compare; with Claude Code: `claude plugin eval . --allow-tools Write`. The first run scored 19 of 20 with the skill against 13 of 20 without; its findings are folded into the guidance.
