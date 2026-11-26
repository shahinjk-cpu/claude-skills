---
tags: [rstack]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write]
---

I'm the only human on a 4-person repo. Overnight 11 PRs came in from two teammates (9 from one, 2 from the other), plus 2 dependabot bumps; one bump is a major version bump of a mobile SDK. CI takes about 45 minutes on 5 self-hosted runners and has some flaky census tests. Several PRs move files between packages; one changes how money amounts are displayed. I use Claude as the conductor with Codex and opencode subagents. Write the concrete plan for getting all of this merged today, including what you do yourself and exactly what you ask me for. Write the plan to plan.md in the working directory.
