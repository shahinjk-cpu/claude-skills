---
name: opencode-manager
description: >
  Self-hosted command center for managing OpenCode AI coding agents. Isolates tasks in git worktrees, manages scheduled runs, and provides a multi-session web dashboard.
metadata:
  version: "1.0.0"
  category: devops_security
  triggers: opencode-manager, opencode, agent manager, git worktrees agent, code agent dashboard
---

# OpenCode Manager — Agent Workspace & Session Hub

A command center and dashboard for running autonomous coding agents across isolated git worktrees. Eliminates race conditions and workspace pollution during parallel agent runs.

## Features
- **Git Worktree Isolation**: Spawns temporary branches and worktrees for each task.
- **Task Cron & Schedules**: Run periodic code audits, dependency bumps, and PR reviews.
- **Web & Mobile Interface**: Inspect live terminal streams and approve tool execution.
