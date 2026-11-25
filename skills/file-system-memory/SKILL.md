---
name: file-system-memory
description: >-
  Structured file-based external memory architecture for AI agents, replacing fragile vector databases with human-inspectable markdown and JSON files.
---

# File-System Memory Architecture for AI Agents

Provides AI agents with permanent, durable memory using the local filesystem instead of complex, opaque vector databases.

## Directory Structure
```
.agent_memory/
├── identity.json         # Agent persona, core mission, constraints
├── state.json            # Active session state, task queue, step count
├── decisions.log.md      # Immutable chronological append-only decision record
└── entities/             # Structured markdown profiles for project components
    ├── auth_system.md
    └── database_schema.md
```

## Update Protocol
- Always read `state.json` on session resume.
- Append completed actions and rationale to `decisions.log.md`.
