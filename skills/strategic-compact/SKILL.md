---
name: strategic-compact
description: "Decide when to run /compact: at phase boundaries, never mid-implementation, plan written to a file first. Use when a long session nears its context limit or the user asks about context hygiene."
---

# strategic-compact — compact on purpose, not by accident

Derived from ECC `strategic-compact` (original: `references/ecc-strategic-compact.md`), adapted to this machine. The original's `suggest-compact.js` PreToolUse hook is **not installed** (not part of the skill folder, and this setup already has many hooks). The guidance below works without it.

## When to compact
| Transition | Compact? |
|---|---|
| Research → Planning | Yes (research is bulky; the plan is the distilled output) |
| Planning → Implementation | Yes — **after the plan is written to a file** |
| Implementation → Testing | Maybe |
| Debugging → next feature / after a failed approach | Yes |
| Mid-implementation | **No** (loses variable names, paths, partial state) |

## Procedure
1. Persist first: plan/decisions → a file in the project (or the memory system). Do not rely on a task list surviving; recent Claude Code versions removed the todo tools by default.
2. Run `/compact <what to focus on next>` (give a one-line focus).
3. After compaction, re-read the plan file; don't re-read everything.

## What survives
CLAUDE.md, files on disk, memory files, git state. Lost: reasoning, file contents already read, tool history, verbal preferences — so write them down.

## Extra token hygiene for this setup
- Biggest recurring costs here: long skill listing, MCP tool lists, large tool outputs. Prefer `lean-web-search` for web input, Headroom (`headroom wrap claude`) for tool-output compression, and keep CLAUDE.md lean.
- Audit duplicate instructions between `~/.claude/CLAUDE.md`, project CLAUDE.md and skills; remove overlap (see memory note on the earlier 42-skill cleanup).
- New third-party skills: install as a thin router + `references/` (loaded on demand), not as many top-level skills.
- Optional hook (not installed): the original script warns at ~160k tokens on a 200k window; ask before adding hooks to settings.json.
