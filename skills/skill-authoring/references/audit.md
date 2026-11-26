# Audit: Review an Existing Skill

Read `references/prose.md` alongside this.

---

## Stage 1: Read the target in full

1. **Read** `SKILL.md` and every reference file. Do not audit from a summary or a grep.
2. **Record** stages, flags and the stages each one skips, review gates, halts, and frontmatter fields in use.

---

## Stage 2: Classify the prose

Walk every sentence that is not an instruction. Classify each as **mechanism** or **motivation** by the test in `references/prose.md`.

For each motivation sentence, decide by the three dispositions in `references/prose.md`:

- **Rewrite** — it implies a limit or discriminator no other rule states. State it as an action, a clear limit, or constraint.
- **Extract** — it carries a rule inside the justification. Keep the rule, cut the rest.
- **Cut** — the rule stands alone without it.

**Never delete a constraint while cutting prose.** When in doubt whether a sentence carries a rule, rewrite rather than cut.

---

## Stage 3: Check the structure

- **Unnumbered actions.** Is any action written as a prose sub-clause — "and post it to X", "then spot-check Y" — rather than a numbered step (principle #2)?
- **Stage completeness.** Does each stage have Work, and Emit/Halt where it reports or fails?
- **Review gates without emit blocks.** A stage that says "stop and sync" with no template leaves the output unspecified.
- **Halts described rather than written.** "Stop and tell the user" is not a halt string.
- **Compression as prose.** Where a paragraph asks the reader to judge how much of the workflow to run, raise it as a question: a flag for the lighter run, or one full run with the judgement removed (principle #5).
- **Router bloat.** `SKILL.md` over ~120 lines, or carrying stage detail.
- **Frontmatter.** Check against `references/frontmatter.md` — especially `allowed-tools` used where `disallowed-tools` was meant.
- **Rules that pull their weight.** A rule stating what the agent would do anyway is costing clarity from the rules around it (principle #10).
- **Creative Metaphor.** Is any figurative label standing in for a literal term — "the spine", "the skeleton", "is a smell" (principle #8)? Replace with the literal term, or cut; never keep it as "deliberate vocabulary". A role term defined once and used consistently (e.g. "conductor") is not metaphor.
- **Declarative where an instruction is meant.** A mechanism written as a description or existential claim — "there is no plan file", "the agent has X" — instead of a direct action (principle #8)? Rewrite as the imperative it implies ("do not create a plan file"), or cut.
- **Stage sends the reader to rationale.** Does any stage instruct the reader to consult `references/rationale.md` for information it needs to run (principle #7)? `rationale.md` never loads, so stages must stand alone — none may say "see rationale.md for …". The router's one optional "why → rationale.md, not required reading" cross-link is allowed.

Differing wording between files is not a finding. Raise it only where two words for one thing make the reader ask whether they are two things.

---

## Stage 4: Emit the findings

Emit the block below.

```markdown
## Stage 4 review: audit — {skill name}

**Defects:** {none, or numbered:}
1. {file}:{line} — {what is wrong} → {proposed change}

**Prose:** {none, or numbered, continuing the numbers:}
2. {file}:{line} "{quoted}" → rewrite: "{the constraint stated as an action}"
3. {file}:{line} "{quoted}" → extract: "{the rule kept}"
4. {file}:{line} "{quoted}" → cut

**Questions:** {none, or:}
- Q1. {the decision} — I would {recommendation}

**Recommended:** {numbers}

Reply with numbers, "defects", or "all".
```

- **Number continuously across sections**
- **Quote the actual text**
- **If a section is empty** use `none`.

---

## Stage 5: Review gate — Confirm before applying

**Stop**: Do not change, edit, or rewrite a skill without confirmation.

Present the emit block from Stage 4 and wait. Advance only on an explicit affirmative.

Where a cut is a judgement call — a passage that blocks a specific wrong inference rather than merely justifying a rule — flag it as a judgement call rather than deciding silently.

---

## Stage 6: Apply

1. **Apply** only the confirmed changes.
2. **Move** motivation displaced by a cut or an extract into `references/rationale.md`, creating it with the not-load-bearing banner if it does not exist. A rewrite displaces nothing.

**Halt** if the rationale file does not exist and the skill has no reference directory:

```
Audit halted at Stage 6: nowhere to move displaced motivation.
Create references/rationale.md with the not-load-bearing banner first,
or confirm the motivation should be deleted outright rather than relocated.
```

---

## Stage 7: Report

```
{skill}: applied {numbers}
kept as mechanism: {list — the ones a reader might expect to be cut}
open: {numbers not applied, or: none}
```

Name what was kept, and why it survived.
