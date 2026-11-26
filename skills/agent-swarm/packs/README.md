# Swarm packs

A pack is a team of roles for one kind of work. Each role runs on one of the shipped base agent types and adds its own rules, model and verifier. Switch packs with `/swarm use <pack>`. Make your own with `/swarm new <name> "<what the team does>"`.

## Format

```markdown
---
name: my-pack                # lowercase, dashes
description: One line: what this team is for.
triggers: [keyword, keyword] # words in a task that auto-pick this pack
extends: general             # optional: inherit roles, then add or override
quality: my-pack-quality.md  # optional: quality bar file, same folder
---

## Roles

### role-name
- type: builder | scout | verifier | researcher | writer | operator
- model: cheap | standard | strong
- verifier: other-role-name   # optional; default is the base verifier
- rules:
  - One rule per line, 3-8 lines. These go at the top of the agent's brief.

## Pairings
- What kind of task goes to which role, then which role checks it.

## Guardrails
- Pack-wide rules added to every brief.
```

Base types map to agent types:

| type | agent type | tools |
|---|---|---|
| builder | `agent-swarm:swarm-builder` | Read, Edit, Write, Grep, Glob, Bash |
| scout | `agent-swarm:swarm-scout` | read-only |
| verifier | `agent-swarm:swarm-verifier` | read-only |
| researcher | `agent-swarm:swarm-researcher` | WebSearch, WebFetch, Read, Write |
| writer | `agent-swarm:swarm-writer` | Read, Write, Edit (no shell) |
| operator | `agent-swarm:swarm-operator` | all session tools, including MCP connectors |

A role may name any other registered agent type instead, for example `type: my-plugin:my-agent`.

Model roles: `cheap` = haiku, `standard` = sonnet, `strong` = the session model. The `cost` profile can change these.

## Where packs live (first match wins)

1. `<project>/.claude/swarm-packs/<name>.md` (shared with the repo)
2. `~/.claude/swarm-packs/<name>.md` (yours, in every project)
3. this folder (built in)

A pack with the same name as a built-in one replaces it. Use `extends` to keep the built-in roles and add your own. A role defined again in the child pack replaces the parent's role of that name.
