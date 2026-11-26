# Anchored decisions — step-by-step guide

How to build software and make decisions that stay aligned with the current state of development,
so resuming work costs minutes instead of re-running the whole discovery process.

---

## 0. The problem this solves

Written decisions drift from code in exactly two ways:

| Drift | What happened | Fix |
|---|---|---|
| **Stale decision** | The note was true in September; the code moved | make staleness *detectable* — anchors |
| **Unrecorded decision** | Code moved, nobody wrote it down | make write-back part of the change, not a follow-up |

Everything below is machinery for those two fixes. The governing rule:

> **Never write down what can be derived.** Derived state (branches, PRs, deploys, call graphs)
> regenerates and self-corrects. Hand-written state decays silently. Push as much as possible
> across that line.

The split in practice:

| Kind | Example | Lives in |
|---|---|---|
| Decision + rationale | "ITs touching SQL use Testcontainers, never mocks" | `DECISIONS.md` (hand-written) |
| Constraint learned the hard way | the `withReuse(true)` gotcha | `CLAUDE.md` (hand-written) |
| Open question needing a decider | "appt_date vs booking date" | `OQ-xx-*.md` (hand-written) |
| Branch / PR / deploy state | "TASK-014 uncommitted on the api module" | git, the forge, your PR/issue dashboard — **never typed** |
| Code structure | who calls `finalize_order` | a code-intelligence index or `rg` — **never typed** |

---

## 1. Starting a ticket

```bash
anchor-check --init
```

Fill `CLAUDE.md` in this order — it is written for a reader who has never seen the ticket:

1. **What this ticket is** — the problem in business terms, modules touched, HDA/Jira ids.
2. **Mandatory** — constraints that are *not* an implementation choice for whoever codes next.
   Each one should also become a `D-xx` with an anchor.
3. **Scope as a diff against what is deployed:**

   ```markdown
   - Deployed today: web v1.87.14 in prod (confirm: the deploy dashboard)
   - This ticket adds: the Ilori brand ("I") to the marketing-tab gate
   - Explicitly out of scope: the all-brands variant drafted on 10-13
   ```

   Scope stated against a design doc is uncheckable; stated against a deployed version anyone can
   confirm it in thirty seconds.
4. **Pointers** — links/commands for the derived state. Never copies of it.

---

## 2. Recording a decision — at the moment it is made

Add the `D-xx` when you choose, not when you finish. A decision recorded later is a decision
reconstructed, and reconstruction is where the *why-not* disappears.

```markdown
## D-03 — Online NEE confirm must set Schedule.confirmed inside doSave()
- Status: ACTIVE
- Decided: 2026-09-09
- Verified: 2026-11-06 (prod)
- Supersedes: D-01
- Superseded-by: —
- Owner: <who made the call>
- Anchors:
  - code: src/checkout/session.py#finalize_order
  - test: tests/integration/conftest.py#postgres_container
  - ship: core v1.86.5
  - env: prod@2026-11-06 — residual ~29/day, down from ~10k backlog

**Why:** finalize_order() never set the flag on the async path, so order counts diverged from
the ledger rows and the nightly job re-sent confirmations.

**Why not:** fixing it in the nightly job (D-01) looked cheaper, but the job also overwrote
realigned reschedules — one bug would have masked the other.

**Still-true test:** reading `src/checkout/session.py#finalize_order` shows the assignment on the
async branch.

**Blast radius if wrong:** every async checkout, fleet-wide; visible as order-count drift in the
nightly reconciliation report.
```

### Field rules

| Field | Rule |
|---|---|
| `Status` | `ACTIVE` · `PROPOSED` (decided, not yet true in code) · `SUPERSEDED` · `REVERTED` |
| `Decided` | when the call was made |
| `Verified` | when it was last *checked against reality*, plus where: `(prod)`, `(qa)`, `(local)`, `(code-only)` |
| `Anchors` | at least one; machine-checkable kinds preferred |
| `Why` | the reason that cannot be reconstructed from the diff |
| `Why not` | the rejected alternative and what ruled it out — **the highest-value line in the file** |

### Anchor kinds

Machine-checked (`code` `test` `sql` `config` `file`): path, optionally `#symbol`. The checker
verifies the path exists, the symbol still appears, and whether the file was committed *after* the
`Verified` date.

Manual (`pr` `jira` `env` `data` `ship` `doc` `url`): give each its own date —
`env: prod@2026-11-06 — …`. These expire after `--max-age` days so stale claims about live
environments surface instead of being quietly trusted. This matters specifically because QA and
prod diverge: a decision verified on QA is a *hypothesis* about prod.

---

## 3. Resuming — the tiered re-entry protocol

**Tier 0 — always, ~2 minutes**

```bash
sed -n '1,60p' the steering file
anchor-check <WORKSTREAM>
git log --oneline --since=2026-11-06 -- src/checkout
```

If everything is `ok`/`man`, the recorded decisions are trustworthy inputs — start working.

**Tier 1 — only for flagged decisions**

```bash
rg -n "confirmed" src/checkout/session.py
```

Did the code move under the decision, or did the file merely get touched nearby? Reading the
anchor's current source answers it.

**Tier 2 — only if Tier 1 is inconclusive**

Recover the original reasoning — session transcripts, the PR thread, the issue history — re-derive, then **supersede** the record. Do not
edit the old decision in place — the superseded record is where the why-not survives.

> The entire point of the tiers: you pay for depth only where the check found evidence of drift.
> That is what stops every change from re-running the full discovery process.

---

## 4. Superseding

```markdown
## D-07 — <the new rule>
- Status: ACTIVE
- Decided: 2026-11-25
- Verified: 2026-11-25 (qa)
- Supersedes: D-03
...

## D-03 — <the old rule>
- Status: SUPERSEDED
- Superseded-by: D-07
**Why it was replaced:** <what we learned that the original decision did not know>
```

The checker treats `SUPERSEDED`/`REVERTED` records as history: structure is validated, anchors are
not re-checked. History stays cheap.

---

## 5. Open questions

One file per question, `OQ-xx-<slug>.md`, with `Kind: engineering-open | needs-a-decider`.

- **engineering-open** — we can settle it with evidence. Record the commands/queries used so the
  evidence can be re-run, not just re-read.
- **needs-a-decider** — a business or product call. Never resolve it by writing code; name the
  decider, list the options with consequences, and surface it.

When answered: write the answer in the OQ **and** promote it to a `D-xx` with anchors. An answered
OQ that never became a decision is how answers get lost.

---

## 6. Write-back — the rule that keeps everything true

> A change that invalidates a decision updates that decision **in the same commit**.

Concretely, when a PR is ready:

1. Which `D-xx` did this change touch? Bump `Verified:` (with the env you actually checked) or add
   a superseding record.
2. Did anything become decided that is not yet recorded? Add it now.
3. Re-run the checker; it must exit `0` for the decisions this ticket owns.

```bash
anchor-check <WORKSTREAM> --quiet || echo "fix before commit"
```

Optional gate — `.git/hooks/pre-commit` in the ticket repo, or a CI step:

```bash
#!/usr/bin/env bash
anchor-check --quiet --max-age 120
```

---

## 7. Command reference

```bash
anchor-check.py                      # every tickets/*/DECISIONS.md (_TEMPLATE skipped)
anchor-check.py <WORKSTREAM>             # one ticket
anchor-check.py path/to/DECISIONS.md # one file
anchor-check.py --max-age 60         # stricter expiry window
anchor-check.py --quiet              # only what needs attention
anchor-check.py --json               # machine-readable, for the board or CI
```

Exit `0` = everything verifiable is current · `1` = something needs attention · `2` = usage error.

---

## 8. Anti-patterns

| Anti-pattern | Why it hurts | Instead |
|---|---|---|
| Branch/PR status typed into `CLAUDE.md` | rots within a day; one wrong line discredits the whole file | link the board |
| Decision with no `Why not` | next session re-litigates the rejected option | always record what was ruled out |
| Editing a decision in place when it changes | destroys the history that explains the current shape | supersede |
| `Verified: (staging)` used to justify prod behaviour | environments diverge | re-verify per environment, record which |
| Writing the decisions at the end of the ticket | by then they are reconstructions | record at the moment of choosing |
| Resolving a `needs-a-decider` OQ in code | silently makes a business call | surface it to the named decider |
