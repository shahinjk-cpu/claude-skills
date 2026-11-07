---
name: mcp-security
description: "Security-review MCP setups: audit .mcp.json for secrets/injection/unpinned packages, review MCP server source, QA a server before release. Use when installing, auditing or publishing MCP servers."
---

# mcp-security — 3 awesome-copilot skills (MIT) as one router

Source: `github/awesome-copilot` → `skills/mcp-security-audit`, `mcp-implementation-security-review`, `mcp-release-qa` (community-contributed; originals unmodified in `references/<name>/main.md`, no scripts).

| Situation | Read |
|---|---|
| "Is this MCP config / server entry safe to add?" (`.mcp.json`, `~/.claude.json`, plugin `.mcp.json`, `claude mcp list`) | `mcp-security-audit` |
| You wrote or are reviewing MCP server/client/tool handler **source code** | `mcp-implementation-security-review` |
| Before shipping/releasing an MCP server (runtime vs docs vs source, failure paths, evidence) | `mcp-release-qa` |

## Local rules
- **Read-only first.** Audit configs by reading them; never start an untrusted MCP server to "see what it does". Don't print secret values — report file:line and the key *name* only.
- This machine has many MCP servers (claude-flow, headroom, plugin MCPs, local services). When asked to audit "my MCP setup", enumerate: `~/.claude.json` and project `.mcp.json`, plugin caches under `~/.claude/plugins/`, and `claude mcp list`.
- Treat `npx -y <pkg>` / `uvx` entries as supply-chain exposure (unpinned latest) and flag them with a pinned-version suggestion.
- Report format: finding · severity · evidence (file:line) · fix. Do not edit configs without asking.
- Pair with `claude-security` (application code) and `security-threat-model` (system-level), and `mcp-server-dev:build-mcp-server` when writing servers.
