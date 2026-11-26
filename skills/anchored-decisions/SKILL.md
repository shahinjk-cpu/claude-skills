---
name: anchored-decisions
description: Record and verify engineering decisions so work resumes from what was already decided instead of re-deriving it. Use when starting or resuming work on a feature, ticket or workstream, when a choice is made that future sessions must not re-litigate, before building on a prior decision or ADR, when the user says "what did we decide", "is this still true", "why is it built this way", "check the decision anchors", "record this decision", "start a decision log", or invokes /anchored-decisions. Works in any repository; wraps the anchor-check CLI.
---

# Anchored decisions

Keeps written decisions aligned with the **current** state of the code, so a returning session
re-derives only what actually drifted. Repository-agnostic: no required folder layout, no
dependencies beyond Python 3.8+.

Two rules carry the whole system:

1. **Never record what can be derived.** Branch/PR/deploy state, which files changed, who calls
   what — all live in git, the forge, and code-intelligence tools. A typed copy rots.
   Record only decisions, their rationale, and hard-won constraints.
2. **Every decision carries anchors** — verifiable handles into the repo — plus a `Verified:`
   date. That turns "is this still true?" into a command instead of an investigation.

## The tool

```bash
anchor-check                 # discover and check every DECISIONS.md in the repo
anchor-check <dir|file|name> # one record set
anchor-check --init          # scaffold a DECISIONS.md here
anchor-check --new "TITLE"   # append a record skeleton with the next free id
anchor-check --quiet         # only what needs attention
anchor-check --json          # for CI or a dashboard
anchor-check --max-age 60    # stricter expiry window
anchor-check --decisions-only    # only DECISIONS.md (alias: --no-feature-map)
anchor-check --feature-map-only  # only FEATURE_MAP.md
```

Discovery also finds `FEATURE_MAP.md` files (the feature-map skill's format) and checks each
entry: its code location must exist (BROK if not), and every `[attr="value"]` selector must still
appear as a quoted string in the code (BROK if renamed or removed). Selectors without an
`[attr="value"]` part are `man`; placeholder entries are `MALF`.

If `anchor-check` is not on PATH, run `anchor-check.py` from this skill's own folder.
Exit code `1` whenever something needs attention — usable as a pre-commit hook or CI gate.

Root resolution: `--root`, else the nearest `.anchors.json`, else the nearest `.git`, else cwd.
Anchors resolve relative to the repo root first, then to the record file's own directory, so both
single-repo and monorepo layouts work unchanged.

## Per-repo configuration (optional)

Only needed when records do not live at a discoverable `DECISIONS.md`, or defaults need changing.
`.anchors.json` at the repo root:

```json
{
  "paths":        ["tickets/*/DECISIONS.md"],
  "feature_maps": ["FEATURE_MAP.md"],
  "feature_map":  true,
  "exclude":      ["archive/**"],
  "anchor_base":  ".",
  "max_age":      90
}
```

`feature_map: false` turns map checks off. Without the file, discovery walks the tree for files
named `DECISIONS.md` and `FEATURE_MAP.md`, skipping build and vendor
directories and any directory whose name starts with `_` (so templates never report as failures).

## Resuming work — tiered, stop as early as you can

| Tier | When | What |
|---|---|---|
| 0 | always (~2 min) | read the decision log, run `anchor-check`, `git log` the affected paths since the newest `Verified` date |
| 1 | the check flags something | read the flagged anchor's current source — did the code move under the decision, or was the file merely touched nearby? |
| 2 | Tier 1 inconclusive | recover the original reasoning (session transcripts, PR discussion, issue history), re-derive, then **supersede** the record |

Escalate on evidence of drift, never on principle. Most sessions stop at Tier 0.

## Reading the verdicts

| Verdict | Meaning | Action |
|---|---|---|
| `ok` | anchor resolves, file untouched since verification | trust it |
| `man` | needs a human (PR, issue, live environment) | confirm if the decision is load-bearing for this change |
| `STALE` | the anchored file was committed **after** the decision was verified | Tier 1 |
| `BROK` | path gone, or symbol renamed/removed | Tier 1–2 |
| `EXP` | verification older than `max_age` | re-confirm, especially live-environment claims |
| `MALF` | missing Status/Verified, no anchors, ACTIVE-but-superseded | fix the record |

## Writing a decision

Add the record **when the choice is made**, not at the end of the work. Required: `Status`,
`Decided`, `Verified` (date + where), at least one anchor, `Why`, and `Why not`.

`Why not` is the one line nothing else on disk records — the diff shows what was built, never what
was rejected. A decision without it gets re-litigated.

Anchor kinds: machine-checked `code` `test` `sql` `config` `file` `doc` (optional `#symbol`);
manual `pr` `issue` `jira` `ticket` `url` `env` `data` `ship` `release` `person` — give these their
own date (`env: prod@2026-01-30 — …`) so live-environment claims expire instead of hardening into
assumed fact.

Templates for a decision log, a steering file and an open question: `templates/` in this skill.

## Write-back rule

A change that invalidates a decision updates it **in the same commit** — bump `Verified:`, or add
a record with `Supersedes:` and set the old one to `SUPERSEDED`. Never delete: the superseded
record is where the why-not lives.

## Open questions

Keep unresolved items as their own records or files, each marked `engineering-open` (we can settle
it with evidence) or `needs-a-decider` (a business call — never resolve it by writing code; name
the decider). When answered, promote the answer to a decision with anchors.

## Scope control

State scope as a diff against what is **deployed** ("prod runs v1.87.14; this adds X"), never
against a design document. Deployed versions are checkable; design intent is not.

## Using with spec-driven-development

When the repo also uses a spec workflow (e.g. `addyosmani/agent-skills@spec-driven-development`,
with `spec/SPEC.md` and `tasks/`), the spec plans *this version*; `DECISIONS.md` holds what must
stay true *across versions*. Do not copy one into the other.

- **Location:** put `DECISIONS.md` in `spec/`, beside the spec. Default discovery finds it.
- **Plan phase:** each choice that will outlive the feature gets a `D-xx` record with `Status:
  PROPOSED`, its anchors and its `Why not` (the spec's plan records risks, not rejected options).
  Set it to `ACTIVE` when the human approves the plan.
- **Tasks:** a task's `Verify:` line is a good `Still-true test` for the decision it implements.
- **Delta specs:** when a delta spec ships, supersede the affected records in the same commit.
- **Resuming:** run `anchor-check` before building on an existing spec; a flagged decision means
  the spec may be stale too.
- **Open questions:** keep them in the spec's Open Questions section, marked `engineering-open` or
  `needs-a-decider`; promote answers to `D-xx` records.
- **Don't record twice:** if an ADR skill (e.g. `documentation-and-adrs`) is also installed, use
  one decision log, not both.

## Using with feature-map

When the repo also uses the feature-map skill (`FEATURE_MAP.md` plus closed-loop verification in
the real app), the map says *where a feature lives and how to reach it*; `DECISIONS.md` says *why
it is built that way*. With spec-driven-development as well: spec → plan (`D-xx` as `PROPOSED`) →
tasks whose `Verify:` uses the map's route and selectors → feature-map's five phases → close.

- **Closing a change:** in the same commit, update the map entry, bump `Verified:` on the affected
  records (or supersede them), and set planned records to `ACTIVE`.
- **Verification level → `Verified:`:** a full before/after run in the app is `(local)` (or the
  environment used); feature-map's `PARTIAL VERIFICATION` is `(code-only)`; `UNVERIFIED`
  leaves the record `PROPOSED`.
- **Map invariants are decisions:** a "critical invariant" in a map entry that must not be
  re-litigated gets a `D-xx` record with anchors and a `Why not`; the map line links its id.
- **Guardrails are anchors:** a lint or CI rule created by feature-map's guardrails workflow is a
  strong anchor (`config: .eslintrc.json#no-restricted-imports`).
- **Keep the map honest:** `anchor-check` checks map entries too, so a moved directory or renamed
  `data-testid` fails the same pre-commit hook and CI gate as a stale decision.

Full procedure with worked examples: `GUIDE.md` in this skill.
