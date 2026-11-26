# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A distributable Claude Code **skill** (`SKILL.md`) plus a stdlib-only Python CLI (`anchor-check.py`)
that verifies hand-written decision records (`DECISIONS.md`) against the current code. Version 1.2.0.
Requirements: Python 3.8+, nothing else; git is optional (only powers the STALE check).

There is no test suite, build step or linter.

## Commands

```bash
python3 anchor-check.py                 # discover + check every DECISIONS.md under the root
python3 anchor-check.py <file|dir|name> # one record set (bare name matches a parent folder name)
python3 anchor-check.py --init [dir]    # scaffold DECISIONS.md (refuses to overwrite)
python3 anchor-check.py --new "TITLE"   # append a record with the next free id
python3 anchor-check.py --quiet | --json | --max-age N | --root PATH
./install.sh [--user | --project <repo> | --cli-only]
```

Exit codes: `0` all verifiable current · `1` any STALE/BROKEN/EXPIRED/MALFORMED · `2` usage/parse error.
To exercise the checker, run it against a scratch directory containing a hand-made `DECISIONS.md`
(and `git init` it to test STALE detection).

## How the pieces fit

- **`anchor-check.py`** pipeline: `find_root` (`--root` → nearest `.anchors.json` → nearest `.git`
  → cwd; nearest marker wins) → `collect`/`discover` → `parse_decisions` (line-based regexes) →
  `check_decision`/`check_anchor` → `report` or JSON.
- **Record format is defined by regexes**, not a schema: headings `## <ID>-<n> - title`
  (`HEAD_RE`, ID prefix 1–4 uppercase letters), fields as `- Key: value` (`FIELD_RE`), anchors as
  list items indented ≥2 spaces under `- Anchors:` (`ANCHOR_RE`). Text inside `<!-- -->` is ignored.
  Changing the templates' layout means checking these regexes still match.
- **Anchor kinds**: `DERIVABLE` (`code test sql config file doc`) must resolve to a path (and
  `#symbol` must appear as a word-bounded match); STALE when `git log -1` on that file is newer
  than `Verified:`. `MANUAL` kinds only expire after `max_age`, using their own date if present.
  Unknown kind → MALFORMED. Anchors resolve against `anchor_base` from config, then the record
  file's own directory.
- **Feature maps**: `FEATURE_MAP.md` files (the feature-map skill's format) go through
  `parse_feature_map` → `check_map_entry` instead, reusing `Decision`/`Finding` with
  `id="MAP"`, `status="MAP"`. Only fields whose bold label contains `location` (or `ubicaci`, for maps written
  before feature-map was translated to English) (paths)
  or `selector` (indented sub-items) are read; code fences are skipped. Selector values from
  `[attr="value"]` must appear as a quoted literal in non-`.md` files, first under the entry's
  location, then anywhere under the root.
- **Verdict precedence**: BROKEN > STALE > EXPIRED > MALFORMED > MANUAL > OK.
  SUPERSEDED/REVERTED records skip anchor checks (history, not live claims).
- **Discovery pruning** (`PRUNE`): build/vendor dirs, agent-tooling dirs (`.claude`, `.cursor`, …,
  so an installed skill's own templates are never checked), and any dir starting with `_`.

## Things to keep in sync

- The record skeletons `TEMPLATE` and `RECORD` inside `anchor-check.py` duplicate
  `templates/DECISIONS.md`; the anchor-kind lists and verdict table are repeated in `SKILL.md`,
  `INSTALL.md`, `GUIDE.md` and the templates. Change one, update the others.
- `install.sh` copies an explicit file list (`install_files`) — new shipped files must be added there.
- `hooks/pre-commit` looks for `anchor-check` on PATH, then
  `~/.claude/skills/anchored-decisions/anchor-check.py`, and silently passes if neither exists.
- Keep `anchor-check.py` stdlib-only and 3.8-compatible (e.g. no `Path.is_relative_to`; it uses
  `from __future__ import annotations` for `X | None` hints).
