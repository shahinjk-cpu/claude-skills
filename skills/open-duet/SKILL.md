---
name: open-duet
description: Proactive AI agent work-partner architecture based on CopilotKit OpenDuet. Runs background routines, connects to user services (Gmail, Calendar, GitHub), manages task cards, and requests approval for sensitive operations.
metadata:
  version: 1.0.0
---

# OpenDuet: Proactive Work-Partner AI Agent

`OpenDuet` is an open-source template for proactive AI agents built on CopilotKit's OpenBot platform. Rather than waiting passively for user prompts, OpenDuet acts as an always-on co-worker that monitors workflows, executes background maintenance, and keeps the user in the loop.

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\OpenDuet`

## Core Capabilities

1. **Proactive Background Routines**:
   - Monitors connected accounts (Google Workspace, GitHub, Slack) on configurable cron schedules.
   - Flags blockers, unread critical emails, and pending pull request reviews.
2. **Human-in-the-Loop Supervision**:
   - Distinguishes between autonomous non-destructive actions and high-impact operations.
   - Presents interactive action cards asking for explicit user approval before sending emails, merging PRs, or modifying databases.
3. **Co-Pilot Card Feed**:
   - Displays finished tasks, upcoming scheduled actions, and action receipts in a real-time card feed.

## Setup & Running

```bash
cd C:\Users\sahin\.gemini\antigravity\scratch\repos\OpenDuet
pnpm install
cp .env.example .env
pnpm dev
```
