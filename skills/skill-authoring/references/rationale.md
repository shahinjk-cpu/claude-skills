# Rationale

> **Not load-bearing for execution.** The mode files carry what to do; this file
> carries why the standard is shaped this way. Read it when changing the standard,
> not when applying it.

## Where the standard came from

It is reverse-engineered from the [`llm-wiki`](https://github.com/nvk/llm-wiki) plugin's command layer — 23 commands sharing a fixed spine, near-zero rhetoric, and a rationale layer kept deliberately off the execution path. Its `command-prelude.md` states the pattern outright: the file "remains as canonical developer documentation for the protocol, but is not load-bearing for command execution."

The counter-example was a hand-written workflow skill of comparable length in which roughly 45% of the lines were argument — metaphor, justification, and pre-emptive rebuttal of rationalizations the author expected the model to reach for.

## Why motivation costs more than it looks

Motivation is not free context. It loads every time the skill runs, competes with the instructions for attention, and — the expensive part — teaches a reader that this file is a place where prose can be skimmed. A file of pure instruction is read as pure instruction.

The wiki commands are not short: several run past 400 lines. Density, not brevity, is the property that matters.

## Why emit templates

"Stop and sync" leaves the output undefined, so what comes back is whatever seemed reasonable at the time. A template with named fields says what is wanted, and `consumers: N (list them)` says it precisely enough that the answer is the enumeration rather than a summary of one.

It is clarity, not enforcement. A template cannot stop an agent doing something else, and an earlier draft of this standard claimed it could — "harder to fake, because unfilled fields are visible." That framing is wrong twice over: it overstates what a document can do, and it treats the agent as an adversary to be contained rather than an operator to be briefed.

## Why a skill that argues does not work

Persuasion in a skill file is the author anticipating a failure and reaching for words. The words then create the problem they were meant to prevent: "this is not permission to dispatch," stated three ways, makes finding a fourth reading the reader's next move. Naming the thing you do not want puts it on the table.

The fix is to say what you *do* want, once, and stop. Not to argue harder, and not to build a cage — an agent that can pivot is the reason to use one instead of a script.

## Why the audit stops before applying

A skill is a workflow the user designed. Cutting prose from it looks like editing, but the risk is deleting a constraint that was doing quiet work inside a justifying sentence. The gate exists so the user sees the quoted fragments before they are gone.

The judgement-call flag in Stage 5 exists for the same reason: the boundary between negative guard and persuasion is the one place this standard is genuinely uncertain, and the author is better placed to call it than the auditor.

## Why Rewrite is a named disposition

Cut and Extract both assume the constraint is either absent or already written somewhere in the sentence. The case they miss is the constraint that exists only as an implication — "patch notes, not marketing copy" bans benefit claims without ever saying so. Extract finds no clause to lift, so the auditor cuts, and the ban goes with it. Naming Rewrite makes that case visible at the point of decision instead of leaving it to whoever notices.

## Why this skill lives at user level

The structural and prose rules are project-agnostic. Only the examples are drawn from a specific codebase. A project-level copy would trap the standard in one repository and drift from any other copy.

## Why Update is the default mode

A skill gets written once and adjusted five times over the following weeks. Update is the mode this skill spends most of its life in, so it is what an unqualified invocation resolves to. New is the rarer event and says so explicitly; Audit is rarer still.

## Why Update does not conform a foreign-shaped skill

Plenty of skills were authored under a different framework, and their shape reflects a paradigm rather than a mistake. Restructuring one while adding a capability to it is two changes billed as one, and the second was never asked for. The `Noticed` field exists so the observation survives without becoming an edit.

The same reasoning bars Update from entering Audit. An audit proposes cuts across a whole skill; arriving there from a request to add one flag turns a small ask into a review the user did not open.

## Why Audit needs explicit direction

Audit is the only mode that reads a skill looking for things to remove. Reaching it by inference — from "tighten this", or from noticing off-standard prose mid-update — produces deletions the user never requested. Only the words "audit" and "review" route there.

## Why a lighter run is a question

The earlier principle #5, "Add a flag for a lighter run", was read as an instruction to invent one. A skill gained a flag that skipped a check it had no reason to skip, added only to satisfy the principle, and it was later removed. Whether a skill needs a lighter run depends on the skill, so the standard names the candidates at the shape review and the user decides.

## Why --quick was removed

It skipped the structural review, which is the stage that finds unnumbered actions and described-rather-than-written halts. Skipping it produced an audit that read prose and missed defects, under a name that claimed both.
