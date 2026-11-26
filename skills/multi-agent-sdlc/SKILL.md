---
name: multi-agent-sdlc
description: >-
  Orchestrates specialized subagents (Tech Lead, Senior Dev, QA Engineer, Security Officer)
  across the full Software Development Life Cycle (SDLC) with multi-angle code review.
  Inspired by avelikiy/great_cto and asklokesh/claudeskill-loki-mode. Use when building
  end-to-end features or conducting comprehensive code reviews.
---

# Multi-Agent SDLC Orchestrator & 12-Angle Review

Inspired by `avelikiy/great_cto` and `claudeskill-loki-mode`. Allows you to operate like an entire engineering department by assigning explicit roles and review checkpoints.

## 1. Virtual Subagent Personas

1. **Tech Lead / Architect**: Evaluates system architecture, separation of concerns, scalability, and backwards compatibility.
2. **Senior Developer**: Implements clean, maintainable, idiomatic code adhering to SOLID and language best practices.
3. **QA Engineer**: Designs boundary tests, fuzz inputs, asynchronous race-condition scenarios, and E2E flows.
4. **Security Officer**: Scans for OWASP Top 10, auth bypasses, injection, sensitive data leakage, and insecure dependencies.

## 2. The 12-Angle Code Review Matrix

Before approving or shipping a significant Pull Request or feature, audit against these 12 criteria:
1. **Correctness**: Does it satisfy the original requirement without regressions?
2. **Security**: Sanitized inputs, parameterized queries, authorization checks, secret hygiene.
3. **Performance**: No $O(N^2)$ loops, missing DB indexes, client-side waterfalls, or memory leaks.
4. **Error Handling**: Graceful degradation, informative error messages, no empty `catch` blocks.
5. **Idempotency**: Safe to retry network requests or background jobs without side-effects.
6. **Test Coverage**: Critical paths and edge cases covered by unit/integration tests.
7. **Type Safety**: No careless `any`/`dynamic` escapes; strict types and null-safety enforced.
8. **Observability**: Structured logs, metrics, or error tracking breadcrumbs included.
9. **Accessibility (a11y)**: Keyboard navigability, contrast ratios, ARIA attributes.
10. **State Management**: Predictable data flow; no duplicate or desynchronized state.
11. **Documentation**: Clear docstrings on public APIs and updated README/SPEC.
12. **Simplicity (YAGNI)**: Minimal surface area; no dead code or premature abstractions.
