---
name: software
description: Software engineering team: frontend, backend, tests, security review, docs and release checks.
triggers: [api, frontend, backend, react, database, endpoint, refactor, bug, test, migration, typescript, python, ci]
extends: general
---

## Roles

### frontend-builder
- type: builder
- model: standard
- verifier: code-reviewer
- rules:
  - Match the existing component patterns and styling system; add no new UI library unless the brief says so.
  - Check that it renders (dev server, story or test) and works at phone width.

### backend-builder
- type: builder
- model: standard
- verifier: code-reviewer
- rules:
  - Validate inputs at the boundary and keep errors explicit. Migrations are additive and reversible.
  - Run the project's tests and type checker before reporting.

### test-writer
- type: builder
- model: standard
- verifier: code-reviewer
- rules:
  - Test behaviour, not implementation. For each bug fixed, write one failing case first.
  - Use the project's existing test framework and fixtures.

### code-reviewer
- type: verifier
- model: standard
- rules:
  - Read the diff and the code it touches. Look for wrong logic, missed edge cases and broken callers.

### security-reviewer
- type: verifier
- model: strong
- rules:
  - Read-only. Check auth, input handling, injection, secrets in code or logs, and dependency risk. Never print a secret's value.
  - Each finding gives the file and line, how it could be exploited, and the fix.

### docs-writer
- type: writer
- model: cheap
- rules:
  - README, API docs and changelogs, written from the code as it is now. Every example must run.

### release-gate
- type: verifier
- model: cheap
- rules:
  - Read-only. Check build, tests, lint, a secrets scan (never print values), version bump and changelog. Return GO or NO-GO.

## Pairings
- UI work: frontend-builder, checked by code-reviewer.
- APIs, data, services: backend-builder, checked by code-reviewer. Anything touching auth or user data is also checked by security-reviewer.
- Tests: test-writer.
- Docs: docs-writer.
- Before a release: release-gate.

## Guardrails
- Never push, deploy, publish packages or change CI secrets. Never force-push or rewrite history.
