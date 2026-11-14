---
name: inspo-mcp
description: >
  Model Context Protocol (MCP) server for real-world UI/UX inspiration. Gives AI agents access to indexed production design references, color palettes, fonts, and component layouts.
metadata:
  version: "1.0.0"
  category: design_frontend
  triggers: inspo mcp, design inspiration, ui references, frontend inspo, real site layouts
---

# Inspo MCP — Live UI/UX Inspiration for Coding Agents

Provides AI agents with instant access to indexed real-world production websites, mobile UI screens, typography combinations, and component architectures.

## Why Inspo MCP?
Instead of hallucinating generic frontend components, agents query Inspo MCP to inspect real-world design systems (Linear, Stripe, Vercel, Apple) for exact CSS styles, padding, colors, and layout compositions.

## Available Tools
- `search_inspo(query, category)`: Query design patterns (e.g. "hero with bento grid", "pricing table with toggle").
- `get_color_palette(domain)`: Extract the exact hex color tokens of a reference site.
- `get_component_markup(component_id)`: Retrieve Tailwind / React / Vue markup for a reference component.

## Configuration in MCP
```json
{
  "mcpServers": {
    "inspo": {
      "command": "npx",
      "args": ["-y", "@nutlope/inspo-mcp"]
    }
  }
}
```
