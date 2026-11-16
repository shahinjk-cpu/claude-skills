---
name: skill-router
description: Universal Skill Router & Dynamic Dispatcher for Antigravity and Claude Code. Auto-indexes 1020+ skills, dynamically routes user goals to the exact specialized skills (design, backend, db, memory, etc.), and updates the live Skill HUD on screen.
license: MIT
metadata:
  version: "1.0.0"
  role: orchestrator
  triggers: router, skill, dizayn, backend, database, memory, token, auto-route, hansi skill
---

# Universal Skill Router & Dynamic Dispatcher

Orchestrates all 1020+ skills across Antigravity and Claude Code without context budget overflow.

## Operating Protocol

1. **Auto-Discovery**:
   - The catalog at `C:\Users\sahin\.claude\skills_catalog.json` indexes all skills across 11 core categories:
     `design_frontend`, `backend_api`, `database_storage`, `memory_context`, `testing_qa`, `mobile_dev`, `game_3d`, `ai_ml`, `content_media`, `devops_security`, `general_tools`.
   - When a new skill is added to `C:\Users\sahin\.claude\skills\`, `C:\Users\sahin\.claude\find_skill.py` automatically detects the count change and re-indexes instantly.

2. **Dynamic Routing**:
   - For any incoming user task, find the best-matching skills:
     ```bash
     python C:\Users\sahin\.claude\find_skill.py "<user query>" [category] [limit]
     ```
   - Load only the required skill's `SKILL.md` into context using `read_file`.

3. **Live User Visibility (Right-Panel HUD & Badges)**:
   - Always announce the active skill in the chat response:
     `🎯 [Aktiv Skill]: <skill_name> — <rolu>`
   - When running in Antigravity, update the Artifact `Active_Skills_HUD.md` so the user sees the real-time active skill status on the right side of their screen.
