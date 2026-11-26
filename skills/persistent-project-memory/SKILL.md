---
name: persistent-project-memory
description: >-
  Maintains long-term project context, architecture decisions, resolved bugs, and
  progress tracking across sessions in a persistent memory file. Inspired by
  thedotmack/claude-mem. Use when starting a new project, working on long-running
  initiatives, or when the agent needs to recall prior context.
---

# Persistent Project Memory & Context Manager

Inspired by `thedotmack/claude-mem` (~99k ⭐), this skill ensures your AI agent never loses architectural context, project decisions, or ongoing tasks across conversations.

## 1. Project Memory File (`.agents/MEMORY.md`)

In any active project repository, maintain a compact, human-readable context file at:
`./.agents/MEMORY.md` (or `./MEMORY.md`).

### Structure Template
```markdown
# Project Memory: <Project Name>
Last Updated: <ISO Date>

## 1. Architecture & Tech Stack
- Frontend: <Framework, State Management, UI Library>
- Backend / DB: <Runtime, Database, ORM, Auth>
- Key Invariants: <Non-negotiable architectural rules, e.g. "All monetary calculations in cents as integers">

## 2. Active Roadmap & Current State
- [x] Milestone 1: <Completed milestone>
- [/] Milestone 2: <Current in-progress task and active branch>
- [ ] Milestone 3: <Upcoming work>

## 3. Key Decisions & Rationale (ADR Log)
- YYYY-MM-DD: Chose Supabase RLS over custom middleware because X.
- YYYY-MM-DD: Migrated table state from local useState to URL searchParams for shareable filters.

## 4. Known Quirks & Resolved Traps
- Fix for Issue #42: Never use package X with Node 22 without flag Y.
```

## 2. Reading & Updating Protocol
1. **On Session Start**: Check if `.agents/MEMORY.md` exists. If yes, read it first to prime the agent's context with zero token bloat.
2. **On Major Milestones**: After completing a feature, fixing a tricky bug, or making a design decision, update `MEMORY.md` with a concise bullet point.
3. **Keep it Lean**: Cap `MEMORY.md` at under 250 lines. Archive old resolved milestones to `MEMORY_ARCHIVE.md` to conserve context.
