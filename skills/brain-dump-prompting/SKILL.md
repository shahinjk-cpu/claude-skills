---
name: brain-dump-prompting
description: >-
  Single-message front-loaded project anchoring pattern that provides full context, constraints, tech stack, and goals upfront to prevent agent wandering.
---

# Single "Brain Dump" Opening Message Pattern

Prevents AI agents from making false assumptions or asking repetitive clarifying questions by structuring the initial request with full operational context.

## The 5-Part Brain Dump Framework
```markdown
# 🎯 PROJECT BRIEF: [Project Name]

## 1. Core Goal & User
- What does this software do?
- Who is the end user?

## 2. Pinned Technology Stack
- Language, framework, and exact versions
- Database and ORM
- Styling & component libraries

## 3. Hard Constraints & Negative Rules
- What MUST NOT be used (e.g. No Docker, No Redux, No Tailwind v3)
- Performance and memory limits

## 4. Current State & Existing Files
- Where is the code located?
- What is already done vs what is missing?

## 5. First Milestone Deliverable
- The exact success criteria for this turn.
```
