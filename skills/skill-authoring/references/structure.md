# New Skill: Structure

Read `references/prose.md` and `references/frontmatter.md` alongside this.

---

## Stage 1: Establish the shape

Answer before writing:

- **Is it a pipeline or a mode-router?** A pipeline runs stages in order (feature, bugfix, release). A mode-router dispatches on intent (a wiki command set, this skill). Pipelines get numbered stages; routers get a mode table.
- **What are the actions, and which phase does each belong to?** Group a phase's actions into one stage and number them (principle #2).
- **Where does it stop for the user?** Each becomes a review gate stage. Stopping is its first numbered action.
- **What must never happen?** These become halt strings and `disallowed-tools`.
- **What runs with no flag?** Name the default mode or path. A skill invoked bare does something defined.
- **Would a lighter run help?** Note candidate stages to skip for the Stage 2 question. Build no flag yet.

**Stop components go where a stop is needed — no more, no less.** A workflow that runs to completion needs none. A workflow with five decisions needs five. Count is not a quality signal in either direction.

**Halt** if a skill of that name already exists:

```
Skill authoring halted at Stage 1: "{name}" already exists at {path}.
Creating it here overwrites a skill the user owns.
Re-run without --new to update it, or name the new skill something else.
```

**Halt** if the skill has no stop and no halt condition:

```
Skill has no review gates and no halt conditions.
Confirm this is a reference skill, not a workflow skill.
Workflow skills that never stop and never refuse do not need to be skills — they are prompts.
```

---

## Stage 2: Review gate — Shape

**Emit** (required — principle #3):

```markdown
## Stage 2 review: shape — {skill name}

**Lighter run?:** {stages a faster run might skip, and when it would be used — or: none apparent}

**Kind:** pipeline | mode-router

**Stages:** {numbered; actions numbered within each}

**Reviews:** {which stages are review gates, and the decision at each}

**Flags:** {flag — which stages it skips, or: none}

**Default:** {what runs with no flag}

**Refuses:** {halt conditions}

**Files:** SKILL.md + {references to be written}

Confirm the shape, or name what is wrong with it.
```

**Stop**: advance only on the user's explicit affirmative.

**Halt** if you are about to write a file without a reply in hand:

```
Skill authoring halted at Stage 2: shape not confirmed.
Writing the files is not the same as agreeing what to write.
Wait for the user's reply before creating SKILL.md or any reference.
```

---

## Stage 3: Write the router

Write `SKILL.md` to carry only the map and the rules; the work lives in references (principle #6):

1. **Frontmatter.** Per `references/frontmatter.md`. Set `disallowed-tools` for anything the skill must be prevented from doing.
2. **A role statement.** One or two sentences: who the operator is and what they own.
3. **The map.** Stage-range → reference file, as a table. For pipelines, follow it with a plain-text numbered sequence showing skips and review gates.
4. **Core Principles.** Numbered, citable from the references. Each states an action; keep a definition only where it carries something the action does not.
5. **Parse $ARGUMENTS.** Every flag, with what it skips, and what runs with no flag.
6. **Operational Rules.** Flat imperatives that apply across stages.

Link `references/rationale.md` and mark it not load-bearing.

---

## Stage 4: Write the stage files

Group contiguous stages into one reference file. Each stage follows the spine:

- **Work**: what to do, imperative.
- **Emit**: the literal block to output, if the stage reports or is a review gate.
- **Halt**: the exact text to emit on failure, in a fenced block.

Not every stage has all three. Every stage has Work.

**Annotate skips in the stage heading**, not only in the router: `## Stage 4: Build a dependency tree  (skip: --no-tree)`. A flag defined in one place drifts from the other.

**No flag skips a read stage or a review gate.** A flag that removes the step which loads the target, or the step where the user decides, is not compression — it is a different workflow wearing the same name.

### Emit blocks

Give the literal template with named placeholder fields:

```markdown
## Stage {N} review: {name} — {subject}

**{Field that needs the user's decision}:** {what goes here}

**{Field}:** {what goes here, or: none}

{what the user is being asked to do}
```

- **Render as plain markdown, never as a code block at emit time**: a `##` heading that names the stage, each field as a **bold label** followed by its value as prose or bullets, sub-items as bullets. Keep the template itself in a `markdown` fence so it reads as a template, not as structure of the reference file.
- **Lead with what needs the user's decision**, then the rest in the template's order.
- **Write names and paths as plain text** in the emitted block; use code formatting only for something the user would copy and run.
- **The template is the whole contract**: anything absent from it is absent from the output — numbering, section labels, ordering, reply instructions. Do NOT rely on supplying structure at emit time.
- **Name fields for what you want back**: `consumers: N (list them)` says produce the enumeration. `looks good` says nothing.
- **Every field is filled or written `none`.**

### Halt blocks

Literal text (principle #4). Name the stage, the problem, the repair, and the refusal:

```
{Workflow} halted at Stage {N}: {what is missing}.
{The rule that was violated}.
{What to do instead}, then re-run.
```

Add `Do not fix and continue` where the lenient path is tempting.

---

## Stage 5: Write the rationale

1. **Write** `references/rationale.md`, putting nothing in it that a stage needs to run (principle #7). Open it with:

   > **Not load-bearing for execution.** The stage files carry what to do; this file carries why the workflow is shaped that way. Read it when editing the workflow, not when running it.

2. **Move** everything the prose test rejected into it, organized as `## Why {rule}`.

---

## Stage 6: Verify

- `SKILL.md` under ~120 lines.
- Every reference linked from `SKILL.md` with a stated load condition.
- Every emit field names what you want back.
- Every flag's skip set matches the stage-heading annotations.
- No flag skips a read stage or a review gate.
- Run the prose test over the stage files (principle #1).
- Grep for metaphor, "because", "the reason", "it's tempting to", "that is backwards".

**Emit** (required — principle #3):

```markdown
## Stage 6: verify — {skill name} → {path}

**Failed:** {any check above that did not pass, or: none}

**Deviations:** {where the build differs from the shape agreed at Stage 2, or: none}

**Assumed:** {taken on faith rather than checked, or: none}

**Open:** {untested or deferred, or: none}

Reply to change any line.
```
