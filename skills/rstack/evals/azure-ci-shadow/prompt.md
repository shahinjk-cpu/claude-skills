---
tags: [rstack]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write]
---

We want to move our PR description CI check onto a new Azure self-hosted runner fleet, first as an advisory shadow next to the existing AWS runner, then eventually cut over. A teammate wrote the runner controller patch (Go, Azure Functions) and a handoff doc; the fleet needs Terraform in three layers, a GitHub App and an org runner group. I'll be in meetings all day. You have Codex and Claude subagents, the az CLI and Terraform. Design how you'll run this end to end, and say exactly what you need from me. Write the plan to plan.md in the working directory.
