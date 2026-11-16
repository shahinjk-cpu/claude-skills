---
name: 21st-dev-mcp
description: Official 21st.dev (Magic MCP) Model Context Protocol integration and agent skill suite. Search 10,000+ curated React, Tailwind, and shadcn UI components, generate custom UI with AI, and install components directly into the codebase.
metadata:
  version: 1.0.0
---

# 21st.dev MCP & UI Component Suite

`21st.dev` (formerly *Magic MCP*) is the npm for design engineers. It connects AI coding assistants (Claude Code, Cursor, Codex, Antigravity) to over 10,000+ production-grade React, Tailwind CSS, Framer Motion, and shadcn/ui components.

Official website: `https://21st.dev`  
Repository: `https://github.com/21st-dev/magic-mcp` & `https://github.com/21st-dev/skill`

## MCP Server Configuration

You can connect 21st.dev to your agent via remote SSE/HTTP or local stdio:

### 1. Remote HTTP / SSE Endpoint (Recommended)
Add to your `mcp.json` or Claude Desktop configuration:
```json
{
  "mcpServers": {
    "21st": {
      "type": "http",
      "url": "https://21st.dev/api/mcp",
      "headers": {
        "x-api-key": "${API_KEY_21ST}"
      }
    }
  }
}
```

### 2. Local stdio MCP
```json
{
  "mcpServers": {
    "21st-magic": {
      "command": "npx",
      "args": ["-y", "@21st-dev/magic-mcp@latest"]
    }
  }
}
```

## Available MCP Tools

| Tool | Description |
|---|---|
| `search_components` | Query 21st.dev catalog with natural language (e.g. "animated hero with bento grid"). |
| `get_component` | Retrieve the full raw React/Tailwind/CSS source code of any component by ID/slug. |
| `generate_ui` | Ask 21st's design models to synthesize an interactive component matching your prompt and tokens. |
| `install_component` | Automatically run `@21st-dev/cli` to add dependencies and drop the component file in `src/components/`. |
| `list_themes` | Browse and download curated design themes (colors, borders, typography). |

## The 7 Specialized 21st Skills

1. `21st-cli-use`: Command-line discovery and component installation (`21st search`, `21st add`).
2. `21st-ai`: In-editor iterative UI generation, sketching, and refining.
3. `21st-registry`: Publishing personal and team components to 21st.dev.
4. `21st-design-sync`: Extracting local design tokens and exporting as a reusable 21st theme.
5. `21st-ui-build`: Building production screens using 21st catalog + local design system.
6. `21st-ui-explore`: Generating multiple alternative design variants for comparison.
7. `21st-ui-review`: Auditing existing UI for accessibility, token consistency, and polish.

## CLI Usage Examples

```bash
# Search for components
npx @21st-dev/cli search "interactive animated pricing card"

# Install a component directly into your project
npx @21st-dev/cli add @shadcn/pricing-table

# Generate custom UI with AI
npx @21st-dev/cli ai generate "SaaS analytics chart with date range picker"
```
