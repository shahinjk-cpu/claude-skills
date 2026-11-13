---
name: opera-webai
description: Opera WebAI and Opera Neon DevTools MCP integration. Enables coding agents to drive in-browser local AI tasks (opera_chat, opera_do, opera_make, opera_research), page actions, automated debugging, and performance profiling.
metadata:
  version: 1.0.0
---

# Opera WebAI & DevTools MCP Suite

`opera-webai` connects AI coding agents directly to Opera's built-in WebAI features and Opera Neon browser automation through the Model Context Protocol (MCP).

Local repository: `C:\Users\sahin\.gemini\antigravity\scratch\repos\opera-devtools-mcp`

## Opera Neon AI Tools

When connected to Opera Neon via `--browser-url`, the following specialized tools become available:

| Tool | Action |
|---|---|
| `opera_chat` | Dispatches a prompt to Opera's built-in on-device AI and returns the response. |
| `opera_do` | Commands Opera's AI to execute an action on the currently rendered web page. |
| `opera_make` | Prompts Opera's AI to synthesize or generate multimodal content directly in the browser. |
| `opera_research` | Runs background topic research with `local`, `one-minute`, or `deep` investigation modes. |

## Browser Automation & Diagnostics

- **Performance Profiling**: Collects Core Web Vitals (LCP, CLS, INP) and generates actionable optimization suggestions.
- **Accessibility Debugging**: Audits DOM elements for WCAG compliance and contrast ratios.
- **Live Memory & Leak Triage**: Takes heap snapshots and tracks retained DOM detached nodes.

## MCP Server Configuration

Add to your `mcp.json` or Claude Desktop config:
```json
{
  "mcpServers": {
    "opera-devtools": {
      "command": "node",
      "args": ["C:/Users/sahin/.gemini/antigravity/scratch/repos/opera-devtools-mcp/build/index.js", "--browser-url=http://localhost:9222"]
    }
  }
}
```
