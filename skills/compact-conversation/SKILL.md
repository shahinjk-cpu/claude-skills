---
name: compact-conversation
description: >-
  Structured state compaction and context checkpointing protocol that condenses long chat histories into 5-7 decision bullets with active variables.
---

# Compact Conversation & State Checkpoint Protocol

When conversations exceed 50+ turns or approach context budget limits, execute this structured compaction protocol.

## Compaction Output Template
```markdown
## 📌 Context Checkpoint & Active State

### 1. Project Goal
[1 sentence summary of the overarching objective]

### 2. Completed Milestones
- [x] Milestone A: Details & verified paths
- [x] Milestone B: Details & verified paths

### 3. Active Architecture & Key Decisions
- Technology stack & versions
- Configured endpoints and ports
- Stored credentials/environment variables

### 4. Next Immediate Steps
1. Task 1: Concrete actionable command/file edit
2. Task 2: Validation command
```
