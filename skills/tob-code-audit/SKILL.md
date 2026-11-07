---
name: tob-code-audit
description: "Trail of Bits audit methods: understand code first, security differential review of diffs/PRs, false-positive verification, GitHub Actions AI-agent workflow audit. Use for security reviews of web/Python/TS code and workflows."
---

# tob-code-audit — 4 Trail of Bits skills (CC BY-SA 4.0) as one router

Source: https://github.com/trailofbits/skills (copyright Trail of Bits). Licensed **CC BY-SA 4.0**: keep this attribution; derivatives of the text must stay under the same license (license text: `LICENSE-trailofbits-skills-CC-BY-SA-4.0.txt`). Local changes: SKILL.md renamed to `references/<name>/main.md`, Codex `openai.yaml` and logo SVG removed, zero-width characters stripped. Only the 4 general-purpose skills of 85 were taken (the rest are smart-contract/binary/niche; `devcontainer-setup` writes `bypassPermissions` configs and `skill-improver` runs a costly autonomous loop — not installed).

| Situation | Read |
|---|---|
| Starting a review of unfamiliar code: build a ground-truth mental model first (assumptions, invariants, data flow) | `audit-context-building` |
| Review a PR/branch/commit range for security impact; adapts depth to risk | `differential-review` (+ `methodology.md`, `adversarial.md`, `patterns.md`, `reporting.md`) |
| A tool/agent says "vulnerability found" — is it real? | `fp-check` (standard / deep verification, gate reviews, evidence templates) |
| `.github/workflows` using AI agents (Claude Code Action, Codex, Gemini) — injection, `pull_request_target` checkouts, wildcard allowlists, unsafe sandbox | `agentic-actions-auditor` (vectors A–I) |

## Local rules
- Read-only analysis: report findings with file:line evidence; never exploit, run untrusted code, or hit live systems. Fixes only on request.
- Sequence for a serious review: `audit-context-building` → `differential-review` (or `claude-security` for a whole-repo scan) → `fp-check` on each finding before reporting.
- Government project (iqtisad-bot): findings that touch personal data, auth, or the RAG ingestion path are high priority; write reports into the project's `docs/security/` on C: and keep secrets out of reports.
- `agentic-actions-auditor` matters because iqtisad-bot uses GitHub Actions with `@claude` mentions — check those workflows first.
