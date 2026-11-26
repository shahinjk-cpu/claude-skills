# DECISIONS — <WORKSTREAM>

> One `D-xx` record per decision. Every record carries **anchors** (verifiable handles into the
> repo) and a **Verified** date, so `anchor-check.py` can tell you which decisions still hold
> without you re-reading the ticket.
>
> Decisions are append-only: when one stops being true, add a new record that supersedes it and
> set the old one to `SUPERSEDED`. The rejected path is the part no commit, no PR and no index
> records — losing it is what makes the next session re-litigate.

## Anchor kinds

| Kind | Checked how | Example |
|------|-------------|---------|
| `code` | file exists; optional `#symbol` must still appear; flagged if committed after `Verified` | `src/checkout/session.py#finalize_order` |
| `test` | same as `code` | `tests/integration/conftest.py#postgres_container` |
| `sql` | migration/DDL file exists | `migrations/0042_add_refid.sql` |
| `config` | file exists and `#key` still present | `config/app.yaml#queue.name` |
| `file` | any other path that must exist | `e2e/run.sh` |
| `pr` / `issue` | **manual** — confirm on the forge / issue tracker | `pr: api#365` |
| `env` / `data` | **manual** — a claim about a live environment; must carry its own date | `env: prod@2026-11-06 — orders exported correctly` |
| `ship` | **manual** — released version carrying the change | `ship: core v1.91.1` |
| `doc` / `url` | **manual** — external reference | `doc: https://…` |

`code`/`test`/`sql`/`config`/`file` are machine-checked. The rest are listed as manual and expire
after `--max-age` days (default 90) so stale live-environment claims surface instead of being
quietly trusted.

---

## D-01 — <decision in one line, stated as a rule>
- Status: ACTIVE
- Decided: <YYYY-MM-DD>
- Verified: <YYYY-MM-DD> (<env: local / qa / prod / code-only>)
- Supersedes: —
- Superseded-by: —
- Owner: <who made the call>
- Anchors:
  - code: <path/to/source>#<symbol>
  - test: <path/to/test>#<symbol>
  - pr: <repo>#<number>
  - env: <prod|qa>@<YYYY-MM-DD> — <what was observed>

**Why:** <the reason this was chosen — the part that cannot be reconstructed from the diff>

**Why not:** <the alternative that was rejected, and what ruled it out. If this line is empty the
decision will be re-litigated by the next session.>

**Still-true test:** <the cheapest command or query that proves this still holds, e.g.
reading `src/checkout/session.py#finalize_order` shows the flag set on the async branch>

**Blast radius if wrong:** <who notices, and how — clinics, a report, a nightly job>

---

## D-02 — <next decision>
- Status: PROPOSED            # ACTIVE | PROPOSED | SUPERSEDED | REVERTED
- Decided: <YYYY-MM-DD>
- Verified: <YYYY-MM-DD> (code-only)
- Supersedes: —
- Superseded-by: —
- Owner: <name>
- Anchors:
  - code: <path/to/file>

**Why:** <…>

**Why not:** <…>

**Still-true test:** <…>

---

<!-- Superseded records stay in the file, below the active ones, as history:

## D-00 — <the decision that no longer holds>
- Status: SUPERSEDED
- Decided: 2026-08-02
- Verified: 2026-09-09 (prod)
- Supersedes: —
- Superseded-by: D-03
- Owner: <name>

**Why it was replaced:** <what we learned that the original decision did not know>
-->
