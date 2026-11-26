# Update: Change an Existing Skill

Read `references/prose.md` alongside this.

An update is scoped to what the user asked for. Do not review, restructure, or tighten anything the request does not touch (principle #11). Where the target skill's shape differs from this standard, leave the difference in place.

---

## Stage 1: Resolve the target and settle the mode

1. **Match** the target against the project's `.claude/skills/`, then `~/.claude/skills/`, then installed plugin skills. An exact name or path match resolves.
2. **Search by description** when the target names no directory but describes a capability. Read the `description` frontmatter of each candidate skill and find the ones that already cover the request.
3. **Route** to `references/structure.md` when nothing matches.
4. **Confirm** before advancing, unless `--update` was given and the target matched by name or path:

```markdown
## Stage 1: confirm the target — {skill name}

**Change:** {what the user asked for, in one line}

**Target:** {skill name} — {path}

**Matched by:** {name | path | description}

Confirm, or reply "new" to create a skill instead, or "audit" to review this one.
```

**Stop**: advance only on an explicit affirmative.

**Halt** when two or more skills match:

```
Update halted at Stage 1: {N} skills match "{target}".
  {name} — {path}
  {name} — {path}
Name the one to update, then re-run.
```

---

## Stage 2: Read the target in full

1. **Read** `SKILL.md` and every reference file it links. Do not work from a summary or a grep.
2. **Record** the conventions the skill uses: its stage structure, how it annotates flags, its emit block format, and whether it has a reference directory or `references/rationale.md`.
3. **Record** the stages, flags and their skip sets, review gates, halts, and frontmatter fields the change might touch.

Record what the skill does, not what it should do. A structural difference from this standard is not a finding here.

---

## Stage 3: Scope the change and propose it

1. **Place** the change: which file, and which section of it. Add a reference file only where the skill already uses them, or where the change does not fit the file that would otherwise hold it (principle #11).
2. **Trace** what else must change for the change to hold together — a new flag appears wherever the skill already lists flags and in its stage headings; a new stage appears wherever the skill already maps stages; a new emit field appears in the template; a changed halt appears in every stage that references it.
3. **Write** the new prose per this skill's `references/prose.md` — imperative, second person, no metaphor. Move displaced motivation to the target skill's `references/rationale.md` only where the skill already has one.
4. **Emit**:

```markdown
## Stage 3 review: update — {skill name}

**Change:** {what the user asked for, in one line}

**Edits:**
- {file}:{lines} — {what changes}
- {file}:{lines} — {what changes}

**Ripple:** {flag annotations, map entries, cross-references that must follow, or: none}

**New files:** {path — why the change does not fit an existing file, or: none}

**Rationale:** {motivation moved to rationale.md, or: none}

**Noticed:** {unrelated problems seen but not touched, or: none}

Confirm, or name what is wrong.
```

**Stop**: do not edit before an explicit affirmative.

List under `Edits` only what the request touches. Put everything else under `Noticed` and do not act on it.

---

## Stage 4: Apply

1. **Apply** only the confirmed edits.
2. **Apply** the ripple in the same pass, not as a follow-up.

**Halt** when the change needs a file the skill has no place for:

```
Update halted at Stage 4: {what} has no home in {skill}.
The skill has no {reference directory | rationale.md}, and creating one
restructures it further than the change requested.
Confirm the new file, or name where the content should go instead.
```

---

## Stage 5: Check the change and report

Check what changed, and nothing else:

- New prose passes the test in `references/prose.md`.
- A new flag is annotated wherever the skill already annotates flags.
- A new stage appears wherever the skill already maps stages.
- A new halt is literal text, not a description of one.
- A new emit field names what it wants back.
- `SKILL.md` is still under ~120 lines, if it was before.

**Emit**:

```markdown
## Stage 5: update applied — {skill name}

**Applied:** {numbered edits}

**Failed:** {any check that did not pass, or: none}

**Ripple:** {what followed, or: none}

**Checked:** {which checks above ran}

**Noticed:** {carried from Stage 3, still untouched, or: none}

Reply to change any line.
```

An off-standard skill stays off-standard. Recommend an audit; do not run one.
