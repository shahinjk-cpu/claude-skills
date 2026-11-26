---
name: claude-md-slim
description: Shrinks CLAUDE.md files that load into every session by moving workflow instructions into skills, area-specific ones into path-scoped rules or nested CLAUDE.md files, and deleting stale lines, with every change shown for approval. Use when CLAUDE.md is over about 200 lines, instructions get ignored, or the user asks to tidy project instructions.
---

# Slim CLAUDE.md

Everything in a CLAUDE.md that loads at launch is paid for on every request of every session, and Anthropic notes that longer files also reduce adherence. The target is under 200 lines per file, holding only what matters in nearly every session.

Moving text around only saves context if the new home loads on demand:

| Where it goes | When it loads | Saves context? |
|---|---|---|
| `@path` import inside CLAUDE.md | With the CLAUDE.md that imports it | No: imports load together with their parent |
| `.claude/rules/x.md` with no `paths` | At launch | No |
| `.claude/rules/x.md` with `paths:` frontmatter | When Claude reads or edits a matching file | Yes |
| CLAUDE.md in a subdirectory | When Claude touches a file in that subdirectory | Yes |
| Skill in `.claude/skills/<name>/SKILL.md` | When invoked or judged relevant (only its description is always present) | Yes |
| Plain path mentioned in backticks, e.g. `` `docs/release.md` `` | When Claude chooses to read it | Yes |

```
Slim CLAUDE.md:
- [ ] 1. Inventory every instruction file that loads at launch
- [ ] 2. Classify each section
- [ ] 3. Draft the new layout and the moved files
- [ ] 4. Show the diff and line counts; wait for approval
- [ ] 5. Apply, then have the user confirm with /context
```

## 1. Inventory

List `./CLAUDE.md`, `./.claude/CLAUDE.md`, `CLAUDE.local.md`, `~/.claude/CLAUDE.md`, any CLAUDE.md in parent directories, `.claude/rules/*.md` without `paths`, and everything they `@import`. Record lines and approximate tokens (characters / 4) for each.

## 2. Classify each section

| Class | Examples | Action |
|---|---|---|
| A. Every session | build, test and lint commands; repo map; conventions for all code; hard rules | Keep, tightened |
| B. One workflow | PR review steps, release checklist, migrations, deploys | Move to a skill |
| C. One area of the code | API conventions, frontend styling, DB access rules | Path-scoped rule or nested CLAUDE.md |
| D. Reference material | long API notes, glossaries, architecture essays | Move to `docs/`, mention the path in backticks |
| E. Stale or redundant | commands that no longer exist, contradictions, things the model does by default | Delete (list them for approval) |

When a section is borderline between A and anything else, keep it in A. Breaking a rule the team relies on costs more than a few lines of context.

## 3. Draft

Skill for a class B section:

```markdown
---
name: release
description: Steps for cutting a release of this repo: version bump, changelog, tag, publish. Use when the user asks to release or publish.
---
<the moved instructions>
```

Path-scoped rule for a class C section:

```markdown
---
paths:
  - "src/api/**/*.ts"
---
<the moved instructions>
```

Also add a short compaction section to the slim CLAUDE.md if it has none:

```markdown
# Compact instructions
When compacting, keep: open tasks, decisions and their reasons, files changed, failing tests.
```

## 4. Show before applying

```
CLAUDE.md: 412 lines → 138 lines
Moved: 3 skills (release, db-migrations, pr-review), 2 path rules (api, ui), 1 doc
Deleted: 9 lines (listed below with reasons)
```

Then the full diff. Change nothing until the user says yes.

## 5. Apply and verify

Write the files. Ask the user to start a fresh session and run `/context`: the "Memory files" list should show the smaller CLAUDE.md. For a deeper check of contradictions and references to missing files, `/doctor prompt-audit` reviews all instruction files without changing them.
