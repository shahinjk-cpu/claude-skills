# Sub-conductors: each lane window runs its own lane

For big work, the conductor does not drive every agent itself. Each lane window is a **sub-conductor**: a small conductor for its lane that plans its parts, launches its own builders and reviewers, gates them, and hands finished trains to the main conductor. The main conductor stays thin and keeps the decisions that cross lanes.

```
human
  └── main conductor (one window): plan, cross-lane schedule, important decisions, merge queue, human's list
        ├── sub-conductor: billing window ── builders, reviewers (Claude, Codex, opencode, OpenRouter)
        ├── sub-conductor: data window ───── builders, reviewers
        ├── sub-conductor: infra window ──── builders, reviewers
        └── ... as many lanes as the plan has
```

A sub-conductor has to be a full session (a window), because a subagent usually cannot launch subagents of its own. In single-window mode there are no sub-conductors: lanes are groups of subagents and the one conductor runs them all.

## Who decides what

| The sub-conductor decides, inside its lane's spec | It goes to the main conductor |
|---|---|
| Splitting a work item into parts, and their order inside the lane | Scope changes, and anything the plan does not cover |
| Each part's difficulty grade and model, from the config | A plan date that will slip |
| Briefs, and scoping each review to the part's real risks | Anything touching another lane's files, a shared hot file, or a shared generated file |
| Fixing P1s within the spec and applying the review policy | Cross-lane decisions on money, auth, permissions, security, migrations or production data |
| Folding its own reviewed parts into a train, and regenerating generated files once | Migration and version numbers, landing order, merges |
| Its own local test slots, within the caps | Reruns of failed CI (with a cause file), production steps, irreversible acts |
| Small naming and layout choices | Changes to a rule, gate, check, model policy or budget |

Only the main conductor merges and rules on escalated decisions. The main conductor settles process questions and reports the rulings afterward. Route [human-only steps](trust.md#human-steps-and-queue-decisions) through main. Keep drafting and reviewing independent parts while a step waits.

## The contract between them

**Starting a sub-conductor window** (the main conductor writes this brief once):
```
You are the sub-conductor for the <lane> lane. Main conductor: <window name>.
Work items and dates: <from the plan, with links>.
You own: <directories and hot files from the ownership map>. Ask before touching anything else.
Rules: <path to the rules file: models and effort, caps, review policy, test slots>.
Report to the main conductor, one line per event: part reviewed (verdict file), PR ready (number, head sha, base sha), CI result, blocked (question, options, recommendation), lane done.
Keep your lane's handoff file at <path>; update it at every milestone.
You never merge. Every important decision (see the table) goes to the main conductor.
```

**Reports from sub to main**: one line per event, with the evidence path; no restating what main already knows.

**Orders from main to sub.** Send one batch per window with the PR, head, ruling and exact next action. For example, `Rebase #123 onto 4f2a9c1, push once, restart deciding CI`. After each merge, send the new main SHA to every open lane. Link reusable rulings.

**Shared state lives in files**, not in chat: the plan and ownership map (main writes), the ledger (main writes), each lane's handoff file (its sub writes), rulings (main writes), verdict files (reviewers write). Any window can be restarted from these after a crash or a usage limit.

## Keeping it cheap

- The main conductor does not build, and it reads first lines (verdicts, CI waiter results), not diffs or whole logs. Its context is the scarcest in the system.
- Caps apply per window: with N lane windows and a cap of 3 running agents each, up to 3N agents run at once. Watch memory and usage, not the number of windows.
- Every message wakes a window and processes its history again. Batch orders, leave windows idle while background agents run and send one-line reports only at events.
- A bloated window is restarted from its handoff file rather than carried on.

## Pausing, resuming and changing settings for everyone

Main sends the same short order to every sub-conductor, for example: "pause: push your work, let running agents finish, start nothing new", or "resume on <model> at <effort>, token efficient: <rules file>". Each sub replies with one line once it has complied (for example "done: no agents running, everything pushed, handoff at <path>"). Main tracks the replies in the ledger and tells the human when every lane has answered.

## Depth

Two levels, main and lane sub-conductors, cover almost everything. If one lane grows too big, split it into two lanes under main rather than nesting a third level: every extra hop adds delay and loses detail.

## How this goes wrong

| Failure | Prevention |
|---|---|
| A sub decides something important and reports afterwards | The table above goes in every sub's start brief, and main reverses such decisions in a ruling |
| Two subs edit the same file | The ownership map; the plan-reviewer checks it |
| Orders get distorted as they are relayed | Main dictates exact actions, and subs pass briefs to their builders verbatim |
| A sub stalls waiting for main | Subs keep working on their next part, and main answers blocking questions first |
| A sub dies mid-task | Its handoff file and pushed branches; main restarts the window from them |
| Main drowns in chatter | One-line reports, evidence in files, and main reads first lines only |
