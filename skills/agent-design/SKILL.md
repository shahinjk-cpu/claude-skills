---
name: agent-design
description: "Design, audit and govern AI agents: architecture discovery, failure diagnosis, governance/permissions, evaluation loops, pre-execution action checks, runtime hardening. Use for agentos or any agent design/review."
---

# agent-design — 4 awesome-copilot skills (MIT) as one router

Source: `github/awesome-copilot` → `agent-architecture` (16 files), `agent-governance`, `agentic-eval`, `verify-agent-action`. Originals in `references/<name>/main.md` (+ `references/agent-architecture/references/*`); the Copilot-specific `agents/openai.yaml` was dropped. Design/audit only — none of these write the agent for you.

| Need | Read |
|---|---|
| New agent / unclear requirements / "do I even need an agent?" | `agent-architecture/main.md` → Design route (`references/design.md`, `architecture-contract.md`, `architecture-selection.md`) |
| Review an existing agent; it errs, degrades, or falsely says "done" | `agent-architecture` → Audit route (`audit.md`, `diagnostic-review.md`) |
| Permissions, policy checks before tool calls, budgets, audit trail, trust levels | `agent-governance` |
| Quality loops: self-critique, evaluator–optimizer, test-driven agent refinement; acceptance design | `agentic-eval` (and `agent-architecture/references/evaluation-design.md`) |
| Hardening an agent runtime that handles untrusted content: tool gateway, workspace file writes, runtime identifiers, credentials, multi-tenant memory (ECC, MIT) | `agent-security-hardening` |
| An agent wants to run something consequential (deploy, delete, send, purchase, credentials, data mutation) — review before it executes | `verify-agent-action` |

## Local rules
- `agent-architecture` by default ends with a **PDF report + rendered diagram**. Ask before producing files; write them only under the target project on C:. "Chat only" overrides.
- Default stance from the source (keep it): try plain automation, a single call or a fixed workflow before an agent loop, RAG, persistent memory, MCP or multiple agents; every added component needs benefit, cost, verification and a simpler alternative.
- Always specify limits: iterations, time, tokens/money, tool calls, stop rules, and what the user gets when stopped.
- For **agentos**: pair with `ethos` (one `ethos.md` per agent: purpose, boundaries, success criteria) and `langchain-agents` (implementation options). For iqtisad-bot: governance + audit trail matter most (government context, local Ollama).
- Never treat a design or audit as permission to change agent code, settings, or take external actions.
