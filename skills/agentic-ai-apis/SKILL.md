---
name: agentic-ai-apis
description: >-
  Standardized API schemas, tool-use contracts, and webhook integration patterns for AI agent tool calling and external service orchestration.
---

# Agentic AI APIs & Tool Calling Patterns

Architectural patterns for creating reliable, deterministic API integrations for tool-calling AI agents.

## Tool Schema Best Practices
- **Strict Parameter Typing**: Always declare `type`, `required`, and clear `description` for every field.
- **Idempotency Keys**: Require an `idempotency_key` on mutating POST/PUT actions.
- **Structured Error Responses**: Always return JSON `{ "success": false, "error": "...", "retryable": true/false }` so the agent can self-correct.
