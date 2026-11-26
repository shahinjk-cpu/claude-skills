# Anchored Decisions vs Kiro spec-driven development

As of 2026-11-25.

## Summary

They solve different halves of the problem. Kiro SDD plans work forward: it turns an idea into requirements, a design and tasks, and drives an agent through them. Anchored Decisions looks backward: it records why things were built a certain way and checks, by command, whether that is still true in the code.

Kiro has no documented automatic check that specs still match the code; Anchored Decisions has no planning layer. Pick Kiro to structure new feature work inside the Kiro IDE or CLI. Pick Anchored Decisions to keep long-lived decisions honest in any repo and any tool. They combine well.

## What each one is

**Anchored Decisions** is a Claude Code skill plus `anchor-check`, a stdlib-only Python CLI. Decisions live in `DECISIONS.md` files as `D-xx` records with Status, Verified date, anchors, Why and Why not. `anchor-check` resolves each anchor (file, `#symbol`, git history) and reports ok, man, STALE, BROK, EXP or MALF. It ships with templates for a steering file and open questions, a pre-commit hook and an installer. Since v1.1.0 it also checks `FEATURE_MAP.md` files, and since v1.2.0 either check runs on its own with `--decisions-only` or `--feature-map-only`.

**Kiro spec-driven development** is the spec workflow of the Kiro IDE and CLI. A spec lives in `.kiro/specs/<feature>/` as `requirements.md` (or `bugfix.md`), `design.md` and `tasks.md`, written in three phases ([Specs](https://kiro.dev/docs/specs/)). Requirements use EARS notation: "WHEN \[condition\] THE SYSTEM SHALL \[behavior\]" ([Feature specs](https://kiro.dev/docs/specs/feature-specs/)). Around specs sit:

- **Steering** in `.kiro/steering/` (default `product.md`, `tech.md`, `structure.md`), included always, by file glob, manually or automatically ([Steering](https://kiro.dev/docs/steering/)).
- **Hooks** in `.kiro/hooks/` that run a shell command or an agent prompt on events such as file save, tool use or spec task start and end ([Hook types](https://kiro.dev/docs/hooks/types/)).
- **Correctness**, which derives properties from EARS requirements and runs generated property-based tests on demand, IDE only ([Correctness](https://kiro.dev/docs/specs/correctness/)).

## Side by side

The sharpest difference is drift: Anchored Decisions checks records against code by command, and Kiro relies on manual sync.

| Dimension | Anchored Decisions | Kiro SDD |
| --- | --- | --- |
| Main job | Keep past decisions true | Plan and build new features |
| Time direction | Backward: why it is this way | Forward: what to build next |
| Unit | One decision record (`D-xx`) | One spec per feature or bug (3 files) |
| Requirements format | Free prose: rule, Why, Why not | EARS: WHEN … THE SYSTEM SHALL … |
| Rejected options | Required `Why not` field | Not a dedicated field |
| Drift detection | Automatic: STALE, BROK, EXP by command | None automatic; manual Sync Files on tasks |
| Behaviour checks | None; only file, symbol and git date | Optional property-based tests from EARS (IDE only) |
| Task execution | Not covered | Tasks tracked, run in dependency waves |
| Project context | `STEERING.md` template, hand-loaded | `.kiro/steering/` with four inclusion modes |
| Automation | `pre-commit` hook, CI exit code, `--json`, `--decisions-only` / `--feature-map-only` | Agent hooks on file, tool, prompt and task events |
| Tooling needed | Python 3.8+, any editor or agent | Kiro IDE or Kiro CLI |
| History | Append-only; supersede, never edit | Specs edited in place; history is git |
| Cost | Free, MIT | Kiro account; pricing not checked |

## Anchored Decisions: pros and cons

Its strength is that a decision record can be checked by a command; its weakness is that it records only decisions, not what to build.

**Pros**

- **Drift is detectable.** `anchor-check` flags a decision as STALE when an anchored file was committed after `Verified:`, and BROKEN when the path or `#symbol` is gone.
- **Runs anywhere.** One stdlib Python 3.8+ script, no network. It works in any editor or agent, with or without Claude Code.
- **Gates commits and CI.** Exit code 1 on any problem, plus a ready-made `pre-commit` hook and `--json` output.
- **Keeps the why-not.** Every record requires `Why not`, and changes are superseded, never edited away, so rejected options aren't re-litigated.
- **Small and cheap to adopt.** No folder layout is required; one `DECISIONS.md` and `anchor-check --init` is enough.
- **Live-environment claims expire.** Manual anchors (`env`, `pr`, `ship`) go EXPIRED after 90 days instead of hardening into assumed fact.

**Cons**

- **No planning layer.** It has no requirements, design or task breakdown; it assumes those live elsewhere.
- **Shallow checks.** It confirms a file exists, a symbol name still appears and the file is unchanged. It can't tell whether the behaviour still matches the decision.
- **False STALE alarms.** Any commit to an anchored file flags it, even an unrelated edit, so busy files need frequent re-verification.
- **Discipline-dependent.** Records are hand-written; nothing forces one to be added when a choice is made.
- **Regex-based format.** Headings, fields and indented anchors must match exact patterns, or records are skipped or reported MALFORMED.
- **No UI.** Output is terminal text or JSON; there's no dashboard or editor integration yet.

## Kiro SDD: pros and cons

Its strength is a full, agent-driven path from idea to tasks; its weakness is that specs can silently drift from code once the work ships.

**Pros**

- **End-to-end workflow.** Requirements, design and tasks in three gated phases, with Requirements-First or Design-First options ([Feature specs](https://kiro.dev/docs/specs/feature-specs/)).
- **Testable requirements.** EARS statements are precise enough for Correctness to turn them into property-based tests ([Correctness](https://kiro.dev/docs/specs/correctness/)).
- **Agent executes the plan.** Tasks are tracked live, and "run all" executes independent tasks in parallel waves ([Specs](https://kiro.dev/docs/specs/)).
- **Bug work is covered.** Bugfix specs record current, expected and "SHALL CONTINUE TO" unchanged behaviour ([Bugfix specs](https://kiro.dev/docs/specs/bugfix-specs/)).
- **Rich context and automation.** Steering with four inclusion modes, `AGENTS.md` support, and hooks on file, tool, prompt and spec-task events ([Steering](https://kiro.dev/docs/steering/), [Hook types](https://kiro.dev/docs/hooks/types/)).

**Cons**

- **No automatic drift detection.** Keeping specs current means editing them and running Sync Files by hand ([Best practices](https://kiro.dev/docs/specs/best-practices/)). Nothing flags a spec the code has outgrown.
- **Tied to Kiro.** Specs, hooks and steering are driven by the Kiro IDE or CLI; Correctness and Analyze Requirements are IDE only.
- **Feature-scoped, not decision-scoped.** A cross-cutting decision ("ITs use Testcontainers, never mocks") has no natural home except steering prose.
- **No why-not field.** Rejected alternatives can be written in `design.md`, but nothing requires them.
- **Heavier per change.** Three files per feature; Quick Spec exists to skip the approval gates for small work.
- **Hook rough edges.** File hooks fire only on agent-made changes, not manual edits, and the docs use two names for the same trigger ([Hooks](https://kiro.dev/docs/hooks/)).

## Where feature-map fits

[feature-map](https://github.com/nicoliniyo/feature-map) adds what neither tool above covers: proving a change works in the running app, and a map of where each feature lives. Kiro's closest equivalents are its optional property-based tests and hooks; Anchored Decisions v1.1.0 checks feature-map's map.

| Dimension | feature-map | Kiro SDD's closest equivalent |
| --- | --- | --- |
| Main job | Prove a change works in the real app | Correctness tests, plus hooks that run test commands |
| How it verifies | Before/after run of the same scenario: browser (CDP, Playwright), simulator, or the real binary | Property-based tests generated from EARS, run on demand (IDE only) |
| When the check can't run | Report starts with PARTIAL VERIFICATION or UNVERIFIED, plus the steps left; denied permissions are never worked around | Not documented |
| Where features live | `FEATURE_MAP.md`: code location, navigation path, selectors, invariants per feature | Steering `structure.md`, project-level |
| Recurring agent mistakes | Turned into lint or CI rules (guardrails) | Pre Tool Use hooks that can block tools; steering rules |
| Drift check on its own file | `anchor-check` flags missing code locations and renamed selectors | None |
| Tooling needed | Any agent that reads `SKILL.md` | Kiro IDE or Kiro CLI |
| Cost | Free, MIT | Kiro account; pricing not checked |

**Pros**

- **Evidence, not claims.** A change counts as done only after the same scenario passes in the real app, with before/after evidence in the report.
- **Honest when blocked.** PARTIAL VERIFICATION and UNVERIFIED markers say exactly what wasn't checked and how to finish.
- **Deterministic navigation.** Map selectors feed Playwright or CDP directly, and vague reports are matched against them before guessing.
- **Hardens over time.** Repeated mistakes become lint or CI rules, which also make strong anchors for decisions.
- **Tool-agnostic and checkable.** Works in any agent that reads skills; `anchor-check` keeps the map's paths and selectors honest.

**Cons**

- **Doesn't improve correctness on its own evals.** Every agent fixed its task with or without the skill; it made the evidence more thorough, not the fix more likely.
- **Evals predate the English version.** They ran on the earlier Spanish text and haven't been re-run.
- **Partly unchecked map.** `anchor-check` covers code locations and `[attr="value"]` selectors; navigation paths and invariants can still drift.
- **Costly to run.** Starting the real app takes time, tools (browser, simulators) and permissions that CI or sandboxes may deny.
- **No planning.** It works inside a task; deciding what to build is left to a spec tool.

**With the other two:** a spec tool (Kiro or spec-driven-development) decides what to build; feature-map proves each task in the running app, using the map for routes and selectors; Anchored Decisions records why, and one `anchor-check` run checks decisions and the map together, or either alone with `--decisions-only` or `--feature-map-only`. feature-map's results also set the record's `Verified:` level: full run → `(local)`, PARTIAL VERIFICATION → `(code-only)`, UNVERIFIED → the record stays `PROPOSED`.

## Using them together, and recommendation

Recommendation: use Kiro specs to plan and build each feature, and Anchored Decisions to keep the decisions that outlive the feature checkable.

1. Plan the feature as a Kiro spec in `.kiro/specs/<feature>/`.
2. When `design.md` settles a choice future work must not reopen, add a `D-xx` record with anchors to the code and tests that implement it, plus the Why not.
3. Point `anchor-check` at those records with `.anchors.json`, e.g. `"paths": [".kiro/specs/*/DECISIONS.md"]`. This is optional: `.kiro` is not in the skipped-directory list, so default discovery already finds a `DECISIONS.md` there.
4. Run `anchor-check --quiet` from a Kiro Agent Stop or Pre Task Execution hook, and in the git `pre-commit` hook, so drift surfaces before more is built on it.
5. On a STALE or BROK flag, update the record and the spec together, in the same commit.

Choose one alone only when:

- **Kiro only:** short-lived features, a team already in Kiro, and little cross-feature decision history to protect.
- **Anchored Decisions only:** not using Kiro, mixed editors and agents, or a mature codebase where the risk is decisions going stale, not planning new work.

## Sources

Kiro pages read on 2026-11-25: [Specs](https://kiro.dev/docs/specs/) · [Feature specs](https://kiro.dev/docs/specs/feature-specs/) · [Bugfix specs](https://kiro.dev/docs/specs/bugfix-specs/) · [Best practices](https://kiro.dev/docs/specs/best-practices/) · [Correctness](https://kiro.dev/docs/specs/correctness/) · [Steering](https://kiro.dev/docs/steering/) · [Hooks](https://kiro.dev/docs/hooks/) · [Hook types](https://kiro.dev/docs/hooks/types/). Anchored Decisions: [repository](https://github.com/nicoliniyo/anchored-decisions), v1.2.0. feature-map: [repository](https://github.com/nicoliniyo/feature-map), v1.0.0. Kiro pricing was not checked.
