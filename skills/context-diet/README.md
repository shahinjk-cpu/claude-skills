[English](README.md) | [繁體中文](README.zh.md)

# context-diet

Audit and optimize Claude Code memory files to reduce startup token cost.

## Description

Context Diet scans all memory files (CLAUDE.md, rules/*.md, MEMORY.md) used by Claude Code at startup, measures their token footprint, and applies five targeted optimizations: trim academic or reference content, merge same-domain files, convert CJK content to English, promote stable patterns to the right config layer, and delete derivable content. Proven to achieve 25-30% token reduction per run.

## Features

- Token and CJK% audit across all memory files with before/after comparison
- Domain overlap detection to identify merge candidates
- Five optimization actions: Trim, Merge, Convert (CJK→English), Promote, Delete
- Layer check: promotes stable MEMORY.md patterns to global `~/.claude/rules/` or project rules
- Parallel explorer agents for deep cross-file analysis
- Mandatory backup before any modification
- Healthy/warning/critical thresholds per metric (tokens, CJK%, file count, MEMORY.md lines)
- Audit script with `--json` flag for machine-readable output

## Usage

```
/context-diet
```

Trigger phrases:

- "context diet"
- "optimize memory files"
- "減少 token 用量"
- "整理 memory"
- "audit claude config"

## How It Works

Context Diet runs `scripts/audit.py` to establish a baseline token count across all memory files. It then launches 2-3 parallel explorer agents — one per file group (global rules, project rules, MEMORY.md) — each checking every line against criteria: decision-affecting, correct layer, derivable, academic, duplicated, or CJK. Based on findings, it generates a five-action optimization plan with estimated token savings, executes changes backup-first through a staging directory, and re-runs the audit to confirm the reduction.

## Requirements

- Claude Code CLI
- `~/.claude/skills/context-diet/scripts/audit.py`
- `~/.local/bin/python3` (uv-managed Python 3.12)

## License

MIT
