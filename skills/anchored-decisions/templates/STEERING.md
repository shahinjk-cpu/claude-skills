# CLAUDE.md — <WORKSTREAM> (steering)

> Steering file for this ticket: read it before touching any document in this folder or writing
> any code on a `<WORKSTREAM>` branch. It exists so decisions already made don't get re-derived,
> re-litigated, or silently drifted from.
>
> **Rule of this folder: never write down what can be derived.** Branch state, PR state, which
> files changed, who calls what — all of that lives in git, the forge, the issue tracker and a
> code-intelligence index, and any copy typed here starts rotting immediately. This file holds only what *cannot* be derived:
> decisions, their rationale, and the constraints discovered the hard way.

## What this ticket is

**<WORKSTREAM> — <one-line title>** (<issue ids>).
Areas touched: `<module/package>`, `<module/package>`.

**Problem in one paragraph:** <what is actually broken or missing, in business terms — the thing a
returning reader needs before any file in this folder makes sense>

## Mandatory — non-negotiable for this ticket

<!-- Hard constraints that are NOT an implementation choice for whoever codes next.
     Each one should also exist as a D-xx record in DECISIONS.md with a verifiable anchor. -->

- **<Constraint>.** <Why it is non-negotiable, and what breaks if it is ignored.> (see `D-xx`)
- **<Constraint>.** <…> (see `D-xx`)

## Decisions

Decisions live in [`DECISIONS.md`](DECISIONS.md), one `D-xx` record each, every one carrying
anchors and a last-verified date. Before building on any of them:

```bash
anchor-check <WORKSTREAM>
```

Anything the check flags is **not** a trustworthy input — re-verify it first (Tier 1/2 below).

## Open questions

Unresolved items are `OQ-xx-*.md` files in this folder. An OQ is either:

- **engineering-open** — we can resolve it ourselves with evidence, or
- **needs-a-decider** — a business/product call that must NOT be silently resolved by whoever
  codes next. Name the decider in the file.

| OQ | Kind | Blocks | Decider |
|----|------|--------|---------|
| OQ-01 | <engineering-open / needs-a-decider> | <what it blocks> | <name or "us"> |

## Scope — defined as a diff against what is deployed

<!-- Scope stated against a design doc is uncheckable. Stated against the deployed version it is
     a fact anyone can confirm. -->

- **Deployed today:** `<module> v<x.y.z>` in `<env>` (confirm: `<command or board link>`)
- **This ticket adds:** <the delta, in behaviour terms>
- **Explicitly out of scope:** <the thing a reader would otherwise assume is included>

## Re-entry protocol — how to pick this ticket back up

```
Tier 0 (~2 min, always)     read this file → anchor-check.py <WORKSTREAM> → git log on the
                            modules listed above, since the newest Verified date
Tier 1 (if anchors flagged) read the flagged anchors' current source — did the code move
                            under the decision?
Tier 2 (if Tier 1 unclear)  recover the original reasoning (transcripts, PR thread, issues),
                            re-derive, then REWRITE the decision (supersede, never edit in place)
```

Most sessions stop at Tier 0. Escalate on evidence of drift, not on principle.

## Write-back rule

A change that invalidates a decision must update that decision **in the same commit** — either by
updating its `Verified:` line, or by adding a new `D-xx` that supersedes it. Never delete a
decision: superseding preserves the *why-not*, which nothing else on disk records.

## Pointers (derived state — never copied here)

- Work board (PRs ↔ Jira ↔ HDA): your PR/issue dashboard
- Code structure: `a code-intelligence index, or rg`
- Prior sessions on this ticket: session transcripts, the PR thread, the issue history
