# Techniques for hard or unclear work

## Choose the model by difficulty

Not every task deserves the same model. The lane grades each part before briefing the builder. In a single window the main conductor does this. Pick from `difficulty_grades` and the role defaults in `conductor.config.json`.

| Grade | Typical tasks | Model tier |
|---|---|---|
| **Frontier** | writing the plan, a replan, architecture and design calls, threat models, a decision that is expensive to reverse | the very top models available, e.g. Claude Fable or an OpenAI Astra-class model through Codex; use two of them on different families when the call matters |
| **Hard** | money, billing, auth, tokens, permissions, security fixes, migrations, production data, concurrency, a bug nobody has explained | strong models, e.g. Claude Opus |
| **Normal** | ordinary features and fixes with a clear spec | a solid mid-tier model, e.g. Claude Sonnet |
| **Easy** | docs, wording, PR text, exact-spec small fixes, fully specified tests, generated text | cheap models: any model opencode offers (DeepSeek, Kimi, Muse, Qwen, GLM, ...) or an OpenRouter model through the tool-capable adapter |

Rules of thumb:
- Grade up when unsure; a wrong cheap attempt usually costs more than one strong attempt.
- If a task fails twice at one grade, retry it one grade up with a fresh agent, the original brief and both failed reports.
- Use the review policy for reviewer independence and the model grade for difficulty. Use strong models for cause investigations.
- Follow `fallbacks` when a model is refused, unavailable or over its limit. Report the switch and keep the risk and access rules.
- When usage is tight, push Easy and Normal work down first; keep Frontier and Hard on the strongest models.

## Interrogate

For money, security, or a design you do not fully trust, ask the scheduled reviewers to try to break the change. They attack the edge cases, retries, races, permission boundaries and failure paths. A finding counts as a P1 only when it is demonstrated: a failing test, a reproduced request, a script that prints the wrong value. Suspicions that cannot be demonstrated are recorded as questions with the experiment that would settle them. This keeps the plan clear of plausible-sounding false alarms while still catching the real ones.

## Blast radius: check what lies beyond the diff

Before a change to shared code lands, list everything that depends on what it touches: other callers, sibling functions built the same way, data already written by the old code, other services or clients that read it, alarms and dashboards keyed to it. Then establish the single fact that makes the change safe by running real code against it, not by writing an argument. When the same bug exists in a sibling, fix the whole family in the same change and add a check that stops it coming back.

## Decision trail: in the records and locally

Every decision of consequence gets one line: when, what was decided, why, the evidence, who decided (and the human's exact words when it was theirs), and the result once known. Keep it in two places:
- **Locally**, as the conductor's running ledger (one timestamped line per decision, merge, finding or ruling), so a restarted session can pick up exactly where the last one stopped.
- **In the project's records** (a records repository or a `decisions/` folder committed with the plan), so the team and future sessions can see why things are the way they are. Write the records copy as a clean technical record: no private paths, no credentials, no raw chat.

A tab-separated form makes it easy to scan and sort:

```
utc_time	decision	why	evidence	decided_by	result
```

## Reflect: turn each lesson into something that enforces it

At the end of a day or a phase, go back over the corrections, surprises and wasted loops, and route each one to a concrete change: a rule in the project's instructions, a test or lint rule, a config value, a script, or an edit to this skill. Then record the change in the decision trail. A lesson that lives only in chat will be relearned; a lesson turned into a check stops recurring.
