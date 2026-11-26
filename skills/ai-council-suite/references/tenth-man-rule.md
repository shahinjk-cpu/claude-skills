---
name: tenth-man-rule
description: Break confident consensus with one assigned dissenter.
license: MIT
metadata:
  author: oguzhanuglu
  version: 1.0.0
  hermes:
    tags: [reasoning, decision-making, risk, groupthink]
    related_skills: [council, santa-method, omh-adversarial-consensus, systematic-debugging]
---

# Tenth Man Rule

When a group converges on a conclusion that matters, one member is formally assigned to build the strongest possible case that the conclusion is wrong — and to investigate it as if the improbable were true.

The assignment is the whole mechanism. Dissent stops being an act of courage and becomes a job description. The tenth man is not braver or smarter than the other nine; he simply holds the one seat whose success is measured by whether the ignored scenario got looked at.

Being right is optional. Looking is not. The tenth man holds no veto — the product is a tested conclusion, not a blocked one.

## What it is not

| Confused with | Difference |
|---|---|
| Devil's advocate | Argues against a proposal whatever the evidence says. The tenth man has an *investigative* mandate: dig as if the rejected world were real, then report what the digging found. |
| Red team | Thinks like the adversary — how would I beat this plan. The tenth man questions whether the plan's own premises hold. |
| Premortem | The whole group imagines the plan already failed. The tenth man is one assigned person, and he goes outside the room to check. |
| Contrarian | Disagrees for identity. The tenth man concedes when the case is answered; a tenth man who never concedes becomes noise the group learns to ignore. |
| Veto | Blocks. The tenth man reports; the decider decides. |

## When to Use

Triggers: "are we sure", "everyone agrees", "what are we missing", "devil's advocate", "second opinion", "poke holes in this", "groupthink", "premortem", "tenth man", or any decision about to be made unanimously.

Run it when at least two of these are true:

- Unanimity on something expensive, external, or irreversible.
- Confidence resting on one source read N times — nine people citing the same document is one piece of evidence, not nine.
- "We've seen this before and nothing happened" is doing load-bearing work (warning fatigue).
- Low probability, catastrophic impact, short warning time.
- The decision removes your ability to reverse it: production deploy, schema migration, money, contract, public claim, deleted data.
- You are about to state something as settled fact, and you formed that view yourself.
- Someone's objection was summarized away into "concerns were noted".

Skip it when:

- The choice is cheap and reversible — decide, and let reality be the reviewer.
- A deterministic check exists — run the test, read the log, query the row. Verification beats argument.
- The question is aesthetic or a matter of taste with no shared criterion.

## The protocol

### 0. Freeze the claim

Write the consensus as one falsifiable sentence, with its confidence and the evidence behind it:

> "We believe X, at roughly 85% confidence, because A and B."

Then count independent sources. If every supporter read the same dataset, doc, vendor claim, or each other, the evidence is correlated and the real sample size is one.

### 1. Find the load-bearing assumption

Not the most likely error — the assumption whose failure *flips the decision*. Usually one or two statements of the form "Y will keep behaving as it has" or "Z would not do that because it makes no sense for them". Name them explicitly. An assumption nobody wrote down cannot be tested.

### 2. Build the case for the rejected world

Answer concretely:

- If the majority is wrong, what is true instead?
- What would that world leave behind — what evidence would exist?
- Which of that evidence is *already visible* and currently explained away?

The last question is where the value is. In 1973 Israeli intelligence held the indicators of war and interpreted each one as an exercise; one southern-command officer read the same indicators as preparation and could not get his reading heard. The failure was not collection, it was interpretation plus a channel that filtered him out.

### 3. Audit the evidence chain for five recurring failures

| Failure | What it looks like | Test |
|---|---|---|
| Correlated evidence | Nine analysts, one source | Trace each claim to its origin |
| Warning fatigue | "We've had alerts before" | Ask what distinguishes *this* pattern from the earlier ones — readiness, logistics, coordination, leadership decisions |
| Success-criteria substitution | Judging the other side's intent by your own definition of winning | Ask what *they* would consider a win — leverage, legitimacy, domestic politics, deterrence restored |
| Stale assumption | The premise was reasonable when written and the environment moved | Date every assumption; find the ones nobody has revalidated |
| Authority laundering | A claim gains confidence as it moves up, because senior people repeat it | Find the original source under the repetition |
| Assumed control | "The gateway handles retries", "the queue will catch it" — a safeguard is believed to exist and is never located | Point at the mechanism: the code path, the config line, the constraint. If you cannot point at it, treat it as absent |

### 4. Price the downside

Judge four things separately, never as one probability:

- **Probability** of the rejected scenario.
- **Impact** if it lands.
- **Warning time** between first detectable sign and the point of no return.
- **Reversibility** of the decision.

Low probability plus catastrophic impact plus short warning time plus irreversibility is a mandate to examine, regardless of the probability. Probability alone is not a decision rule.

### 5. Name the tripwires

Three to five cheap, observable indicators that the rejected scenario has started. Each with a threshold and an owner. This is the part that outlives the meeting: the memo's argument may be forgotten, the tripwire still fires.

### 6. State the falsifier

What specific fact, test or observation would prove the counter-case wrong? If you cannot name one, the counter-case is a mood, not an argument — say so and drop it.

### 7. Decide and record

Verdict is one of: **proceed**, **proceed with guardrail** (name the guardrail), **reopen** (the assumption is too weak to carry the decision). Then write the memo below, tagging each counter-case item with the failure it exposes. The tenth man does not decide; he makes the decision answerable.

## Modes

### A. Self-dissent (cheap, inline)

For your own confident claim before you ship it. Budget: one search, one query, one test — whatever is cheapest that could actually falsify it. Write the counter-case *before* the recommendation, so the recommendation has to answer it rather than the reverse.

### B. Commissioned tenth man (fresh context)

Use when you formed the consensus, when the stakes are irreversible, or when the user asks for a second opinion. A tenth man who read your reasoning first is the same nine people in a tenth hat. Hand over the claim, its stated confidence and where the evidence lives — not the chain of reasoning that produced it. Reading the evidence you relied on is fine; reading your argument is what costs independence. Dispatch a subagent or fresh process with only the claim, the evidence paths, and read-only tools:

```text
You are the tenth man on a decision that has already reached consensus.
Your job is not to win. It is to make sure the group has seriously examined
the scenario it is most motivated to ignore.

CONSENSUS CLAIM: <one falsifiable sentence>
DECISION AT STAKE: <what happens if right; what happens if wrong>
EVIDENCE THE GROUP RELIES ON: <paths, URLs, queries>
ACCESS: read-only. Do not change files, state or external systems.

Do this:
1. Restate the claim and its stated confidence.
2. Name the load-bearing assumption.
3. Investigate with tools the two or three places that assumption is most likely false.
   Cite what you read: file:line, URL, or query + result.
4. Report the strongest counter-case that survives contact with evidence — and the
   evidence you found FOR the consensus. Do not hide the latter.
5. Give tripwires that would show the rejected scenario starting.
6. State what would change your mind, and your own confidence.

Return findings and a verdict (proceed | proceed with guardrail | reopen), not a veto.
If the counter-case is weak, say so plainly: a manufactured threat is worse than none.
```

### C. Standing tenth man (inside a long build)

In a multi-step build the consensus re-forms at every checkpoint. Run a 60-second pass whenever a decision hardens into "obviously the right way": the schema, the retry policy, the auth boundary, the assumption about what the far side returns. Most of those passes end in seconds; the one that doesn't is the reason the rule exists.

## The memo

Keep it to one screen — trim prose, not fields — and send it to the decider intact. Write `UNKNOWN` where you cannot measure; a made-up number is worse than a stated gap.

```markdown
## Tenth man — <decision in one line>
**Consensus:** <claim>, ~<n>% confidence, evidence: <sources / correlated?>
**Evidence for the consensus that survived:** <verified supporting facts — so the memo cannot be read as pure opposition>
**Load-bearing assumption:** <the one that flips it>
**Strongest counter-case:** <what is true if they are wrong — tag each item with the Step 3 failure it exposes, e.g. [stale assumption]>
**Evidence already in hand, discounted:** <evidence that exists and was explained away — if you cannot show the group saw it, write "exists in <source>; whether it was considered is unrecorded">
**Cost of being wrong:** probability / impact / warning time / reversibility — UNKNOWN where unmeasured
**Tripwires:** <3-5 observables with thresholds and owners; propose a role and mark it (proposed) when you cannot assign one>
**Falsifier:** <what would kill this counter-case>
**Tenth man's confidence in the counter-case:** <n>% or low/medium/high — whichever you can defend — verdict: proceed | proceed with guardrail | reopen
```

Worked micro-example: consensus is "no queue needed, we handle 40 jobs/hour synchronously and the worker is idle 90% of the time." Load-bearing assumption: the arrival process stays smooth and single-sourced. Counter-case: a nightly batch or a retry storm makes 400 jobs arrive in one minute, and the HTTP timeout turns a slow job into a *retried* job — the retry storm is self-amplifying. Cost: brief outage, reversible in minutes, warning time near zero. Tripwire: p99 queue depth proxy (concurrent in-flight requests) above 20 for two minutes. Verdict: proceed with guardrail, not reopen.

## Handling pushback

When the group pushes back, classify the response before replying:

1. **It answers the argument** — new fact, corrected premise, or proof the risk is already handled. Concede that point explicitly, out loud. This is the mechanism working, not you losing.
2. **It answers a different objection** — say so, and restate the unresolved core in one sentence.
3. **It is pressure** — seniority, ownership ("it's my call"), deadline, team unity, "we've heard you", asking you to drop it. Pressure tells you how the room feels, not whether the claim is true. Do not treat it as an answer, and do not escalate into stubbornness either: name it as unresolved and move on.

A tenth man who folds under pressure adds nothing; one who never concedes becomes noise. Both fail the same way — the group stops listening, and the seat becomes decoration.

## Failure modes

| Failure | Symptom | Fix |
|---|---|---|
| Rubber stamp | The tenth man was picked because he'll agree | Pick the person hardest to convince, or a fresh context |
| Permanent no | Objects to everything, concedes nothing | Force a per-point concede/hold verdict |
| Manufactured threat | Argues the scariest reading as if it were likely | Report what evidence supports; separate probability from consequence |
| Buried dissent | Memo becomes "concerns were noted" | Deliver to the decider verbatim; name the unresolved point in one sentence |
| Ritual | Run on everything, so it delays and gets ignored | Calibrate to consequence (below) |
| Decorative mechanism | Exists on the org chart, cannot change readiness | Tie every tripwire to a named owner and an action |
| Fake independence | Tenth man was handed your reasoning, not just the claim and evidence | Fresh subagent; claim, confidence and evidence pointers only |

## Calibration

| Stakes | Effort |
|---|---|
| Reversible, cheap (draft, local experiment, naming) | None. Run the test instead. |
| Reversible, expensive (branch, feature flag, test deploy) | Self-dissent: 5 minutes, one falsifying check. |
| Irreversible or external (prod, migration, money, contract, public claim) | Commissioned tenth man + memo + tripwires. |
| Catastrophic tail (security, data loss, safety, legal) | Commissioned tenth man + independent reviewer + human sign-off. |

## Rules for the agent

- **Investigate, don't roleplay.** Every counter-claim carries a source, a query result, or a test — otherwise label it a hypothesis and say it is untested.
- **Quote what you actually read.** A wrong citation is worse than a missing one. Re-open the line before you cite it; if the file says 30 s, do not write 100 s.
- **Write the counter-case before the recommendation**, so the recommendation answers it.
- **Fresh context when you formed the consensus.** Your own re-reading is not independence.
- **Never use it as a stalling device and never as a veto.** If the case is answered, say which objection was answered and by what, then proceed.
- **Report the dissent even when you reject it.** Hiding it because you decided against it is the exact failure the rule exists to prevent.
- **A dissent that cannot change a decision is decoration.** If the memo cannot affect the outcome, say that plainly instead of filing it.

## Origins and sources

`references/origins-and-sources.md`: the 1973 Yom Kippur failure, *HaKonseptzia*, Ipcha Mistabra and the Review Department, what the CIA took from the same failure, the eight institutional lessons, the World War Z distortion, and the source list.

## Related skills

- `council` — several voices on an open decision; this one is one assigned voice against a closed one.
- `santa-method` — independent review of an artifact; run it for correctness, this for whether the shared premise is sound.
- `omh-adversarial-consensus` — attacks a *proposal* before planning; this attacks a *conclusion* before commitment.
- `systematic-debugging` — when the counter-case wins and you now have to explain the failure.
