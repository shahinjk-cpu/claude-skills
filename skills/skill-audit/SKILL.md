---
name: skill-audit
description: Audit all Claude Code skills for token overhead, cost per invocation, and usage frequency using npx skill-audit. Identifies heavy skills and prune candidates to reduce token spend.
category: memory_context
triggers: skill-audit, audit skills, token cost, skill overhead, token usage frequency
---

# skill-audit

Audit installed Claude Code skills for token consumption, cost projections, and usage frequency.

## Usage
Run directly from terminal or via Bash/PowerShell:
```bash
npx skill-audit audit
```

To specify model and daily session count:
```bash
npx skill-audit audit --model claude-sonnet-4 --sessions 20
```
