---
name: adversarial-review
description: Use before shipping any non-trivial hand-built system (an API, a webhook handler, an automation touching real data, anything with logins or money), when someone says "security review this" / "review before I ship", or when a build is about to be called done without an independent adversarial pass.
---

# adversarial-review: many lenses, verify each finding, trust the journal

For a plain diff review, use your normal code review. This skill is for whole-system passes before shipping, where the risk is in how the pieces fit together.

## Shape

1. **Finder fan-out.** Parallel agents, one lens each, each blind to the others. A standard set (scale it to the build):
   - authorization, object access (IDOR), tenant isolation
   - sessions, crypto, 2FA (including replay)
   - outbound fetches: SSRF, redirects, size limits
   - injection, regex blow-ups, parsing (including signatures checked over a re-serialized body instead of the raw bytes)
   - public surface: exposed routes, secrets in code or logs, debug endpoints
2. **Independent verify per finding.** A separate agent per finding, told to **refute** it against the actual code. Only confirmed findings become work.
3. **Fix, then re-verify the fixes.** Report confirmed, refuted and fixed counts, with file:line evidence.

If your harness has a workflow or pipeline tool, run finder → verify as a pipeline, with no barrier between lenses.

## Recovery rule: a zero is not always a zero

On large runs, verifier agents can die (session limits, timeouts), and the run then reports `confirmed: 0`. That is misleading, not clean. **Never accept a zero-findings result from a run where agents died.** Read the run's per-agent logs or journal, where each agent's actual return value is recorded, and triage the raw findings by hand. Split verification into smaller batches up front so no single agent carries a long tail.

## Verification style

- Test pure logic with fast scripted checks against fixtures, not browser automation.
- When you must test the UI, assert on outcomes (row counts, response codes, stored state), never on markup the same agent wrote. Those pass trivially and prove nothing.
- A finding is confirmed only when someone reproduced the bad behavior or traced the exact code path. "Plausible" doesn't ship a fix.

## Red flags

- "The run said 0 confirmed" after agent deaths: read the journal.
- A fix applied without an independent check of the original finding: you may be fixing a non-bug and missing the real one.
- A review scoped to the diff when the risk is systemic (auth, webhooks, secrets): widen it to the whole surface.
