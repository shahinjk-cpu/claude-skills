# Anchored Decisions

Decision records that can be **verified against the code**, in any repository and any language.

A Claude Code skill plus `anchor-check`, a small stdlib-only Python CLI. Each decision in a
`DECISIONS.md` carries *anchors* (verifiable handles into the repo such as a file, a symbol, a
migration or a config key) and the date it was last verified. `anchor-check` resolves every anchor
and reports which decisions can no longer be trusted. A returning session (human or Claude) then
re-derives only what actually drifted, instead of re-running the whole discovery process.

Requirements: Python 3.8+. No packages, no network, no services. Git is optional; without it the
"changed since verification" check is skipped.

## Why

Written decisions drift from code in two ways:

| Drift | What happened | Fix |
|---|---|---|
| **Stale decision** | The note was true once; the code moved | make staleness *detectable*, with anchors |
| **Unrecorded decision** | Code moved, nobody wrote it down | make write-back part of the change, not a follow-up |

The governing rule: **never write down what can be derived.** Branch, PR and deploy state, and
call graphs, all live in git, the forge and code-intelligence tools. Record only decisions, their
rationale (including what was rejected, the *why not*), and constraints learned the hard way.

## Install

### With `npx skills`

```bash
npx skills add nicoliniyo/anchored-decisions -g   # user scope: every project on this machine
npx skills add nicoliniyo/anchored-decisions      # project scope: the current repo only
```

User scope installs to `~/.claude/skills/anchored-decisions/`. The skills CLI does not put the
`anchor-check` command on your PATH; Claude runs `anchor-check.py` from the skill folder either
way. To use the command yourself, link it:

```bash
ln -s ~/.claude/skills/anchored-decisions/anchor-check.py ~/.local/bin/anchor-check
```

Update later with `npx skills update`.

### With the installer

```bash
git clone https://github.com/nicoliniyo/anchored-decisions.git
cd anchored-decisions
./install.sh                       # user scope: every project on this machine
./install.sh --project /path/repo  # project scope: committed with that repo, shared with the team
./install.sh --cli-only            # just the anchor-check command, no skill
```

User scope installs to `~/.claude/skills/anchored-decisions/` and links the CLI into
`~/.local/bin`. Project scope installs to `<repo>/.claude/skills/anchored-decisions/`. Both are
additive: delete the folder to uninstall.

## Quick start

```bash
cd your-repo
anchor-check --init                     # creates DECISIONS.md
anchor-check --new "Use Postgres advisory locks for job claims"
# fill in the anchors and the why-not, then:
anchor-check
```

A record looks like this:

```markdown
## D-01 - Job claims use Postgres advisory locks
- Status: ACTIVE
- Decided: 2026-11-06
- Verified: 2026-11-06 (code-only)
- Supersedes: -
- Superseded-by: -
- Owner: <who made the call>
- Anchors:
  - code: src/jobs/claim.py#claim_next
  - test: tests/test_claim.py#test_concurrent_claims

**Why:** <the reason that cannot be reconstructed from the diff>

**Why not:** <the alternative that was rejected, and what ruled it out>

**Still-true test:** <the cheapest command that proves this still holds>
```

## Commands

```bash
anchor-check                 # discover and check every DECISIONS.md in the repo
anchor-check <dir|file|name> # one record set
anchor-check --init          # scaffold a DECISIONS.md here
anchor-check --new "TITLE"   # append a record skeleton with the next free id
anchor-check --quiet         # only what needs attention
anchor-check --json          # for CI or a dashboard
anchor-check --max-age 60    # stricter expiry window (default 90 days)
anchor-check --decisions-only    # only DECISIONS.md (alias: --no-feature-map)
anchor-check --feature-map-only  # only FEATURE_MAP.md
```

`anchor-check` also checks `FEATURE_MAP.md` files written by the
[feature-map](https://github.com/nicoliniyo/feature-map) skill: each entry's code location must
exist, and each `[attr="value"]` selector (`data-testid`, `aria-label`, …) must still appear as a
quoted string in the code. A moved directory or renamed selector reports `BROK`.

Exit `0` = everything verifiable is current · `1` = something needs attention · `2` = usage error.

## Verdicts

| Verdict | Meaning | Action |
|---|---|---|
| `ok` | anchor resolves, file untouched since verification | trust it |
| `man` | needs a human (PR, issue, live environment) | confirm if the decision is load-bearing |
| `STALE` | the anchored file was committed **after** the decision was verified | re-read the anchor |
| `BROK` | path gone, or symbol renamed/removed | re-derive, then supersede |
| `EXP` | verification older than `max_age` | re-confirm |
| `MALF` | missing Status/Verified, no anchors, ACTIVE-but-superseded | fix the record |

Machine-checked anchor kinds: `code` `test` `sql` `config` `file` `doc` (optionally pinned with
`#symbol`). Manual kinds, which expire after `max_age`: `pr` `issue` `jira` `ticket` `url` `env`
`data` `ship` `release` `person`. Give manual anchors their own date, e.g.
`env: prod@2026-01-30 — orders exported correctly`.

## Gating commits and CI

```bash
cp hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

```yaml
- run: python3 .claude/skills/anchored-decisions/anchor-check.py --quiet
```

## Per-repo configuration (optional)

Only needed when records don't live at a discoverable `DECISIONS.md`. Copy
`examples/anchors.json.example` to `.anchors.json` at the repo root:

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

`"feature_map": false` turns map checks off. Without it, discovery walks the tree for
`DECISIONS.md` and `FEATURE_MAP.md`, skipping build and vendor directories,
agent-tooling directories such as `.claude`, and any directory whose name starts with `_`.

## What's in here

```
SKILL.md          the skill Claude Code loads (triggers, protocol, verdict table)
GUIDE.md          step-by-step procedure with worked examples
INSTALL.md        install and setup reference
anchor-check.py   the checker CLI
templates/        DECISIONS.md · STEERING.md · OPEN-QUESTION.md
examples/         anchors.json.example
hooks/pre-commit  ready-to-use git hook
install.sh        installer
docs/             kiro-comparison.md
```

Full reasoning and worked examples are in [`GUIDE.md`](GUIDE.md).

## Compared with Kiro spec-driven development

Kiro specs plan new work forward (requirements, design, tasks); Anchored Decisions checks that past
decisions still match the code. They complement each other. See
[`docs/kiro-comparison.md`](docs/kiro-comparison.md) for a side-by-side table, pros and cons of
each, where [feature-map](https://github.com/nicoliniyo/feature-map) fits, and how to use them together.

## License

MIT — see [`LICENSE`](LICENSE).
