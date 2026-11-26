# Prose Standard

Applies to all modes.

## The test

For every sentence that is not an instruction, ask:

**Does knowing this change what I would do in a case the file does not list?**

- **Yes** — keep it.
- **No** — move it to `references/rationale.md`.

## Voice

A sentence that passes the test still has to read as an instruction. Two failures survive the mechanism/motivation cut and must be caught — both are principle #8, neither is a judgement call:

- **Metaphor** — a figurative label ("the spine", "is a smell") for a literal thing. Replace with the literal term, or cut.
- **Declarative for imperative** — a mechanism phrased as a description ("there is no X") instead of an action ("do not create X"). Rewrite to the imperative.

## Examples

Motivation — cut:

> This gate carries the most weight of the four.
> A spec file written into the worktree becomes a second source of truth.
> Because the substance was settled at Stages 6 and 9, this should be near-perfunctory.

Mechanism — keep:

> The default `terminal` threshold deadlocks the chain: task 2 waits for a `terminal` only the conductor produces.
> The linter skips any line containing `lint-allow:`, so assert the marker count did not grow.
> The dispatched agent has no tracker access, so this cannot live in the dispatch stage.

The keepers change what you do next. The cuts make you nod.

## Three dispositions

A sentence that fails the test has three fates. Choose by what it carries.

| The sentence | Disposition |
|---|---|
| Implies a limit or discriminator no other rule states | **Rewrite** — state it as an action, a clear limit, or constraint |
| States a rule inside its justification | **Extract** — keep the rule, drop the rest |
| Only argues the rule is right | **Cut** |

Prefer Rewrite over Cut whenever cutting leaves unanswered a case the sentence answered.

### Rewrite

Extract finds no clause to keep when the constraint was never written down — only implied by the justification. Write it out instead.

1. **Name the case the sentence decides.** Ask what you would get wrong if it were gone.
2. **State it as an action**, listing the specific words or moves banned.
3. **Keep the direction when the rule is asymmetric.** "Hedge down, never up" answers a case that "hedge honestly" does not.

| Before | After |
|---|---|
| Patch notes, not marketing copy. | State what a change does; do not sell it — no benefit claims, no "now you can". |
| Overstating how often a bug hit reads worse than admitting it was an edge case. | When the frequency is uncertain, hedge down — prefer "sometimes" to an unqualified claim, never the reverse. |
| The symptom tells a reader whether they hit this bug. The cause is an autopsy that makes the product sound buggier than it is. | Keep whichever detail lets a reader tell whether they hit this bug; drop the rest — no root cause, no description of the old broken behavior. |

A rewrite longer than the original is still correct when the extra words are the banned cases.

### Extract

| Before | After |
|---|---|
| This is not planning. It establishes that the target is right before planning effort is spent. | This is not planning. Do not produce structure, phases, or integration detail here. |

Shorter and more prescriptive at once is the signal the cut was right.

## Principles

A numbered principle list is not exempt from the test. A clause is mechanism when it supplies the discriminator needed to apply the principle, motivation when it argues the principle is correct.

## Length

Five words instead of fifteen makes the five stronger and harder to misread.

Where you give no guidance, the agent's own judgement fills the space, and usually fills it well. Add a rule only where the default would be wrong. Every rule added weakens the ones already there.
