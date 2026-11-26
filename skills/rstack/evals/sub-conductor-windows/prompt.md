---
tags: [rstack]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write]
---

I run five Claude Code windows on the same repository: one main conductor and four lane windows (web, backend payments, infrastructure, mobile). This week the web and payments lanes both need to change the same shared API types file, and the payments and infrastructure lanes both want to add a database migration. Each lane also uses Codex and opencode subagents. Tell me how the windows should coordinate today, who decides what, and how each lane's work reaches main. Write the plan to plan.md in the working directory.
