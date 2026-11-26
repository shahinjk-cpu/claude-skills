---
name: context-diet
description: "context, diet, rules, optimize, reduce, token, usage, context 太肥, rules 優化, 瘦身"
version: 0.3.0
disable-model-invocation: true
---

# Context Diet

Audit and optimize Claude Code memory files (CLAUDE.md, rules/*.md, MEMORY.md) to reduce
startup token cost. Proven to achieve 25-30% reduction through five actions: trim, merge,
convert, promote, and delete.

## Agent Delegation

Launch 2-3 parallel `explorer` agents for deep cross-file analysis (one per file group:
global rules, project rules, MEMORY.md). Optimization writing runs in main context.

## Workflow

### Step 1: Audit

Run the scanner to get baseline metrics:

```bash
~/.local/bin/python3 ~/.claude/skills/context-diet/scripts/audit.py
```

Review output for:
- **Total tokens** — target: <10k for memory files
- **CJK% >2%** — any file with significant CJK needs English conversion
- **Domain overlaps** — files sharing 2+ domain keywords are merge candidates

For JSON output (machine-readable): add `--json` flag.

### Step 2: Analyze (Parallel Agents)

Launch parallel explorer agents, one per file group:

1. **Global rules** (`~/.claude/rules/*.md`) — internal redundancy, academic content, verbosity
2. **Project rules** (`<project>/.claude/rules/*.md`) — overlap with global rules, derivable content
3. **MEMORY.md** — entries that should be promoted to rules, stale entries, duplicates

Each agent checks every line against these criteria:
- **Is it a decision-affecting rule?** Keep only if removing it would cause wrong behavior.
- **Is it in the right layer?** Stable rules in MEMORY.md → promote to rules/. (See Step 3: Promote)
- **Is it derivable?** Code structure, git history, general knowledge → remove.
- **Is it academic/reference?** Theory, taxonomy tables, attribution lines → remove.
- **Is it duplicated?** Same content in another file → keep in one place only.
- **Is it in English?** CJK rules content → convert to English (saves ~40% tokens).

### Step 3: Plan Optimizations

Based on agent findings, produce a plan using all five action types:

| Action | Criteria | Example |
|--------|----------|---------|
| **Trim** | Academic content, inline configs, verbose examples | Remove CEK taxonomy table |
| **Merge** | 2+ files covering same domain | security + security-hardening → security |
| **Convert** | CJK → English in rules/CLAUDE.md | Chinese instructions → English |
| **Promote** | Cross-project rules in MEMORY.md → global rules/ | Universal dev patterns → ~/.claude/rules/ |
| **Delete** | Derivable from code or duplicated | Directory listing in CLAUDE.md |

#### Promote: The Layer Check

Project MEMORY.md accumulates knowledge across sessions. Over time, stable patterns
emerge that should be **promoted** out of memory into rules — but to the right level:

| Rule applies to... | Promote to | Example |
|---------------------|------------|---------|
| All projects (universal) | `~/.claude/rules/*.md` (global) | "CLI-first, MCP only when no CLI alternative" |
| This project only | `<project>/.claude/rules/*.md` | "Alembic latest: x5p6q7r8s9t0" |
| Neither (changing state) | Keep in MEMORY.md | Module status table, version numbers |

**After promotion, MEMORY.md should only contain:**
- **Changing state** — module status, version numbers (will update)
- **Index pointers** — links to topic files (no inline content)
- **Project-specific preferences** — behavioral corrections tied to this project only

Estimate before/after token counts for each change.

### Step 4: Execute (Backup-First)

**MANDATORY**: Always backup before modifying.

**Safety-pin check**: Run `~/.local/bin/python3 ~/.claude/scripts/verify-safety-pins.py` before and after the rewrite — FAIL means a pinned anchor got deleted, roll back from the backup.

```bash
# 1. Backup
mkdir -p /tmp/rules-backup/{global,project,memory}
cp ~/.claude/rules/*.md /tmp/rules-backup/global/
cp <project>/.claude/rules/*.md /tmp/rules-backup/project/
cp <memory>/MEMORY.md /tmp/rules-backup/memory/

# 2. Create optimized versions in staging
mkdir -p /tmp/rules-staging/{global-rules,project-rules,memory}
# Write new files to staging first

# 3. Verify staging (keyword grep for critical content)
# For each merged/promoted file, grep for key concepts from source files

# 4. Replace only after verification passes
cp /tmp/rules-staging/global-rules/*.md ~/.claude/rules/
# Delete merged source files (e.g., rm ~/.claude/rules/old-file.md)
```

### Step 5: Verify

Re-run audit to confirm improvement:

```bash
~/.local/bin/python3 ~/.claude/skills/context-diet/scripts/audit.py
```

Compare total tokens against Step 1 baseline. Target: 25-30% reduction.

## Optimization Principles

1. **English-only** — Rules are for Claude, not humans. English = ~40% fewer tokens than CJK.
   Exception: proper nouns like「少爺」,「繁體中文」.
2. **Decision-only** — Keep rules that change Claude's behavior. Remove FYI/reference content.
3. **Right layer** — Universal rules → `~/.claude/rules/` (global). Project-specific rules →
   `<project>/.claude/rules/`. MEMORY.md → changing state, index pointers, project-specific preferences only.
4. **Single source of truth** — Each concept lives in exactly one file. Cross-reference, don't duplicate.
5. **Merge same-domain** — Files with 70%+ domain keyword overlap should merge.
6. **Progressive disclosure** — Detailed reference → move to topic files loaded on-demand.

## Quick Reference

| Metric | Healthy | Warning | Diet needed |
|--------|---------|---------|-------------|
| Total tokens | <10k | 10-15k | >15k |
| CJK% | 0% | 1-5% | >5% |
| File count | <20 | 20-25 | >25 |
| Overlap domains | 0-2 | 3-4 | >4 |
| MEMORY.md lines | <50 | 50-80 | >80 |

## Scripts

- **`scripts/audit.py`** — Scan all memory files, report tokens/CJK%/overlaps. Use `--json` for machine output.
- **`scripts/context_budget.py`** — Read-only budget report across the whole system-prompt surface:
  rules (full text), CLAUDE.md, MEMORY.md, every skill's frontmatter name+description (per-turn cost,
  tagged hot/cold/ref), agent definition files, and a count of commands. Paths resolve from `Path.home()`
  (cwd-independent). Token estimate is a rough chars/4 (CJK counted as 1 char, so CJK cost under-estimated).

  ```bash
  ~/.local/bin/python3 ~/.claude/skills/context-diet/scripts/context_budget.py         # human table
  ~/.local/bin/python3 ~/.claude/skills/context-diet/scripts/context_budget.py --json  # full structure
  ```
