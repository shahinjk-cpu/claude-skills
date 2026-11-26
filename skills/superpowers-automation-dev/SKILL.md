---
name: superpowers-automation-dev
description: >-
  Enforces structured software engineering (Brainstorm -> Plan -> TDD -> Clean Code ->
  Verify) inspired by obra/superpowers, and designs resilient automation systems,
  background pipelines, bots, scrapers, and API integrations. Use when building
  software features, debugging complex bugs, or architecting automated workflows.
---

# Superpowers Software Engineering & Automation Architect

Inspired by `obra/superpowers` (~296k+ ⭐), this skill combines disciplined software craftsmanship with resilient automation pipeline engineering.

## 1. The Superpowers Development Loop

Follow this 4-step loop for any non-trivial feature, bugfix, or system build:

### Step 1: Clarify & Scope (Brainstorm)
- Identify inputs, outputs, edge cases, and failure modes before writing implementation code.
- If requirements have critical ambiguity, ask concise clarifying questions upfront.

### Step 2: Micro-Plan
- Break complex work into small, independently verifiable tasks (2–5 minutes each).
- Identify exact files to create or modify and how they connect to existing modules.

### Step 3: Systematic Implementation & Root-Cause Debugging
- **Clean Architecture & SOLID**: Keep business logic pure and testable; isolate external I/O (databases, HTTP APIs, filesystem, UI) behind clean interfaces.
- **Root-Cause Debugging Rule**: Never apply a "shotgun fix" or guess-and-patch. Reproduce or trace the exact failure path, identify the root cause, fix it at the source, and verify no regressions were introduced.

### Step 4: Verification Before Completion
- **Never claim a task is done without verification**:
  - Run static analysis / linters / typechecks (`dart analyze`, `tsc --noEmit`, `ruff`, `pytest`, etc.).
  - Execute unit/integration tests or a dry-run script to prove the code actually works.

## 2. Automation Systems & Pipeline Engineering

When building automated bots, cron workflows, data scrapers, or API integrations:

1. **Idempotency**:
   - Design every automation so running it twice on the same input does not duplicate records, double-send emails/messages, or corrupt state (use unique deduplication keys or upsert logic).
2. **Resilience & Error Recovery**:
   - Wrap external network calls (APIs, webhooks, scraping targets) with **timeouts**, **exponential backoff with jitter**, and rate-limit (`HTTP 429`) handling.
   - Fail gracefully: if 1 item in a batch of 100 fails, log the error with context and continue processing the remaining 99 items.
3. **Observability & Structured Logging**:
   - Emit clear start/progress/summary logs (`Processed: 98, Skipped: 2, Failed: 0, Duration: 3.4s`) so unattended runs (including Antigravity Scheduled Automations) are easy to audit.
4. **Security & Secrets Hygiene**:
   - Never hardcode API keys, tokens, or passwords in scripts or commits. Load secrets from `.env` or environment variables and validate their presence at startup with a clear error message if missing.
