# Anchored Decisions — install

Decision records that can be **verified against the code**, in any repository, any language.

Requirements: Python 3.8+. Nothing else — no packages, no network, no services.
Git is optional (its absence only disables the "changed since verification" check).

## What's in here

```
SKILL.md              the skill Claude Code loads (triggers, protocol, verdict table)
GUIDE.md              step-by-step procedure with worked examples
anchor-check.py       the checker CLI
templates/            DECISIONS.md · STEERING.md · OPEN-QUESTION.md
examples/             anchors.json.example — per-repo config, copy to .anchors.json
hooks/pre-commit      ready-to-use git hook
install.sh            installer (user scope, project scope, or CLI only)
```

## Install

```bash
./install.sh                       # user scope: every project on this machine
./install.sh --project /path/repo  # project scope: committed with that repo, shared with the team
./install.sh --cli-only            # just the anchor-check command, no skill
```

`--user` (the default) installs to `~/.claude/skills/anchored-decisions/` and links the CLI into
`~/.local/bin`. `--project` installs to `<repo>/.claude/skills/anchored-decisions/` so teammates
get it on checkout. Both are additive and reversible — delete the folder to uninstall.

Without Claude Code, `--cli-only` is enough: the checker is a plain script.

## First run

```bash
cd your-repo
anchor-check --init                     # creates DECISIONS.md
anchor-check --new "Use Postgres advisory locks for job claims"
# fill in the anchors and the why-not, then:
anchor-check
```

## Per-repo configuration (optional)

Only if records don't live at a discoverable `DECISIONS.md`:

```bash
cp examples/anchors.json.example .anchors.json
```

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
`DECISIONS.md` and `FEATURE_MAP.md`, skipping build/vendor directories and any
directory whose name starts with `_` (so templates never report as failures).

## Gating a commit or a build

```bash
cp hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
```

CI (any provider — the tool is a script and an exit code):

```yaml
- run: python3 .claude/skills/anchored-decisions/anchor-check.py --quiet
```

Exit `0` = everything verifiable is current · `1` = something needs attention · `2` = usage error.

## Anchor kinds

Machine-checked against the tree, optionally pinned to a symbol with `#`:
`code` `test` `sql` `config` `file` `doc`

Need a human, and expire after `max_age` days so they can't harden into assumed fact:
`pr` `issue` `jira` `ticket` `url` `env` `data` `ship` `release` `person`

Give the manual ones their own date — `env: prod@2026-01-30 — orders exported correctly`.

## The method in four lines

1. Never record what can be derived (branch state, PR state, call graphs) — link it instead.
2. Every decision carries anchors and the date it was last verified.
3. Resume in tiers: read + check (always), read the flagged anchor (on a flag), recover the
   original reasoning (last resort).
4. A change that invalidates a decision updates it in the same commit — bump `Verified:`, or
   supersede. Never delete: the superseded record is where the *why not* lives.

Full reasoning and worked examples: `GUIDE.md`.
