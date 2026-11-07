---
name: context-engineering
description: "Reference for agent context design: degradation, compression, budgeting, file-based context, memory architectures, tool design, harnesses, multi-agent isolation. Use when designing agents or cutting token use (e.g. agentos)."
---

# context-engineering — 10 skills from `muratcankoylan/Agent-Skills-for-Context-Engineering` (MIT) as one router

Docs-only install: each skill's `SKILL.md` + `references/` are in `references/<name>/`. The repo's example scripts, tests and `install.sh` (contains `rm -rf`, an `eval`) were **deliberately not copied** — where a reference mentions `scripts/*.py`, they exist upstream only. Zero-width characters were stripped from the copies.

| Question | Read |
|---|---|
| What is context, what goes in it, token economics | `context-fundamentals` |
| Why does quality drop in long contexts (lost-in-middle, poisoning, distraction, clash) and how to detect it | `context-degradation` |
| How to compress/summarize long histories without losing task state; how to evaluate compression | `context-compression` |
| Budgeting, observation masking, KV-cache-friendly layout, compaction triggers | `context-optimization` |
| Durable scratchpads/plans/tool-output offloading to files | `filesystem-context` |
| Persistent memory: vector/graph/temporal, retrieval, consolidation | `memory-systems` |
| Writing tools/descriptions agents use correctly; consolidating tools | `tool-design` |
| Designing autonomous agent harnesses and research loops | `harness-engineering` |
| Splitting work across agents to isolate context (supervisor, swarm, handoff) | `multi-agent-patterns` |
| Loops where the agent/harness improves itself safely | `self-improvement-loops` |

## How it fits this setup
- Operational token savers already installed: `strategic-compact` (when to /compact), `lean-web-search` (small inputs), Headroom (tool-output compression), caveman/ponytail (terse output). Use this reference for *design decisions* (agentos, new agents, memory choices), not for per-session tweaks.
- Memory landscape here is already crowded (auto-memory, `.remember/`, Obsidian sync, Goodmem, OpenMemory): read `memory-systems` before adding another store, and prefer consolidating.
- Pair with `agent-design` (architecture/governance) and `langchain-agents` (implementation options). Remote specifics (hosted agents, BDI, book-SFT, "latent briefing") were not copied.
