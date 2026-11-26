---
name: skill-souffleur
description: Keeps Claude Code skills loaded and applied across context compaction and session resume.
---

# skill-souffleur

# skill-souffleur

Keeps Claude Code skills loaded and in use for the whole session, including after the context is compacted or the session is resumed.

In a theatre, the souffleur sits out of sight at the edge of the stage and gives an actor the line they forgot, at the moment they need it. Souffleur does the same for skills: when compaction drops a skill the current task needs, it brings the skill back.

> **Status:** work in progress, no release yet. See the [roadmap](#roadmap).
>
> **Early access.** Souffleur is a Claude Code mod: TypeScript that runs inside Claude Code through its mod API, shipped and installed as a plugin. Anthropic still changes that API between releases, so an update of Claude Code can break Souffleur until it is adapted. It is provided as is, with no guarantee of fixes or dates. [docs/compatibility.md](docs/compatibility.md) lists the versions each behaviour was checked on.

## The problem

Claude Code loads a skill's instructions into the context when the skill is invoked. Long sessions compact that context, and the skill text does not reliably come back. Tested on Claude Code 2.1.322 with a 43 KB skill:

- In a running session, compaction re-attaches the skill cut off at 20,000 characters. The model no longer sees the rest.
- When a session is resumed and then compacted, the skill is not re-attached at all.
- Claude Code re-attaches at most 5,000 tokens per skill and 25,000 tokens across all skills. Skills that do not fit the budget are dropped.
- Invoking the skill again restores the full text.

The skill list itself comes back after compaction since Claude Code 2.1.304. What gets lost is the content of skills you already used. The model then keeps working without rules it followed an hour earlier, and nothing tells you. Related upstream reports: [#94564](https://github.com/anthropics/claude-code/issues/94564), [#82144](https://github.com/anthropics/claude-code/issues/82144), [#74990](https://github.com/anthropics/claude-code/issues/749
