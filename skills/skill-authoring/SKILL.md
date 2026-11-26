---
name: skill-authoring
description: Update an existing Claude Code skill, write a new one, or audit one against a fixed structural and prose standard. Use when the user says "update the X skill", "add X to the Y skill", "change how the X skill works", "write a skill", "create a skill for X", "make a skill", "turn this into a skill", "audit this skill", "review this skill", or is editing a SKILL.md.
argument-hint: "[<skill name or path>] [--update] [--new] [--audit]"
allowed-tools: Read, Write, Edit, Grep, Glob, Bash(ls:*), Bash(wc:*)
---

# Skill Authoring

A skill's purpose is to instruct an operator, not convince them. It carries what to do, what not to do, and what to emit. Everything that argues the rule is right belongs in a rationale file that does not load at runtime.

A skill is not a vehicle for agent enforcement. It cannot make an agent comply, and so should not try. Instructions should be clear such that following them is the natural result of reading them.

Three modes. Route on the flag, or by the routing rules below.

| Mode | Trigger | Reference |
|---|---|---|
| **Update** — change an existing skill | `--update`, or "update", "add", "change", "adjust" | [`references/update.md`](references/update.md) |
| **New** — build a skill from scratch | `--new`, or "new", "create", "write a skill for X" | [`references/structure.md`](references/structure.md) |
| **Audit** — review an existing skill against the standard | `--audit`, or "audit", "review" | [`references/audit.md`](references/audit.md) |

All three modes load:

- [`references/prose.md`](references/prose.md) — the mechanism/motivation test and how much to write.
- [`references/frontmatter.md`](references/frontmatter.md) — verified field semantics. Do not assume these from memory.

Thoughts on why the standard is shaped the way it is live here: [`references/rationale.md`](references/rationale.md). This file is not and should not be load-bearing.

## Routing

1. **Take the flag** when one is given.
2. **Otherwise match** the request against the trigger words in the table.
3. **Route to New** when no existing skill matches the target.
4. **Default to Update** when nothing above decides it, and confirm the mode at Stage 1 before reading further.

Enter Audit only on `--audit`, or on the user asking to audit or review a skill. Never enter Audit from Update — recommend one instead.

## Core Principles

Cite by number from the reference files.

1. **Keep skills mechanistic, and keep motivation elsewhere.** Keep a sentence that changes what you would do in a case the file does not list. Move one that only makes you agree with the rule to `references/rationale.md`.
2. **Number each action.** When one stage includes more than one action, number each action so order and execution are clear.
3. **Use fields in emit templates.** Write the emit template with fields to ensure key data is always presented. Name each field for the thing it should contain.
4. **Write the exact text a halt emits.** Do not describe the failure and leave the wording open.
5. **Ask the user whether a lighter run is worth having.** At the shape review, name any stage a faster run could reasonably skip and when it would be used, and let the user decide. When a lighter run exists, make it a flag, not prose asking the reader to judge how much of the workflow to run.
6. **Put the map, principles, flags and operational rules in `SKILL.md`.** Put the work in references, read at first use.
7. **A stage should be runnable without rationale.**  Don't put anything in `references/rationale.md` that a stage needs to run. No stage should send the reader there for an instruction.
8. **Do not use metaphor.** Write in the imperative, second person, present tense.
9. **Don't trust frontmatter without the definition.** Read `references/frontmatter.md` before relying on any field.
10. **Say it once, briefly.** Add a rule only where the default would be wrong.
11. **Edit within the skill's existing structure.** Add a reference file, a router split, or `references/rationale.md` only where the skill already has them, or where the change does not fit what is there.

## Parse $ARGUMENTS

- **target** — skill name or path. Everything that is not a flag.
- **`--update`** — change an existing skill. Routes to `references/update.md` and skips the Stage 1 mode confirmation.
- **`--new`** — build from scratch. Routes to `references/structure.md`. Use it to force a new skill when the target matches an existing one.
- **`--audit`** — review an existing skill. Routes to `references/audit.md`.

## Operational Rules

- Read the target skill in full before proposing any change to it.
- Propose the revision before applying it. Skills encode a workflow the user owns; a silent rewrite loses their intent.
- Keep `SKILL.md` under ~120 lines. Past that, split to references.
- Never delete a constraint while cutting prose. Rewrite a sentence as an action when it implies a limit no other rule states; extract the rule when a sentence states one inside its justification.
- A skill that needs no references is fine. Do not split a 60-line skill into a router and one file.
- Supporting files never auto-load. Every reference must be linked from `SKILL.md` with a statement of when to read it.
- Annotate every skippable stage in its own heading as well as in the router. A flag defined in one place drifts from the other.
- No flag skips a read stage or a review gate.
