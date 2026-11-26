---
name: spec-driven-development
description: >-
  Enforces spec-driven engineering and context management for large software and game
  projects. Inspired by gsd-build/get-shit-done and shanraisshan/claude-code-best-practice.
  Use when beginning complex multi-file features, apps, or game mechanics before writing code.
---

# Spec-Driven Development (PRD -> Spec -> Micro-Tasks -> Code)

Inspired by `gsd-build/get-shit-done` and `shanraisshan/claude-code-best-practice` (~67k ⭐). Prevents rabbit-hole debugging by turning loose ideas into a verifiable technical spec before touching code.

## 1. The 3-Step Spec-Driven Workflow

### Step 1: Technical Specification (`SPEC.md`)
Before implementing a feature that touches >2 files, produce a concise 1-page spec:
1. **Problem Statement & Scope**: What are we building, and what is explicitly OUT of scope?
2. **Data Model / Schema**: Entities, fields, types, and DB/state migrations.
3. **API Contracts / Component Tree**: Input props/params, return values, errors.
4. **Edge Cases & Failure Modes**: Network failure, empty state, permission denied, invalid inputs.

### Step 2: Atomic Task Breakdown
Break the spec into a numbered task list where each task:
- Can be implemented in a single turn.
- Touches 1–3 specific files.
- Has an explicit verification command (e.g., `npm test tests/auth.test.ts` or `dart analyze`).

### Step 3: Phase Execution & Checkpoints
- Execute one atomic task at a time.
- Verify immediately.
- Mark the task `[x]` and commit or checkpoint before moving to the next.
