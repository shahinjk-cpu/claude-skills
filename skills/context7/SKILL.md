---
name: context7
description: >
  Version-exact documentation and snippet retrieval MCP server. Pulls fresh, version-specific library docs and examples directly into agent context, eliminating hallucinations.
metadata:
  version: "1.0.0"
  category: ai_ml
  triggers: context7, library docs, api documentation, upstash context7, version exact docs
---

# Context7 — Live Version-Exact Documentation & API Reference

Fetches up-to-date, version-specific documentation, type definitions, and code examples for any library or framework directly into the agent's context.

## Problem Solved
Prevents outdated or hallucinated API usage (e.g. Next.js App Router vs Pages Router, Tailwind v3 vs v4, LangChain / Pydantic v1 vs v2 breaking changes).

## Tool Calls
- `context7_get_docs(package_name, version, query)`: Retrieves authoritative snippets and API signatures.
