---
name: design-extract
description: >
  Extract complete W3C design tokens, Tailwind configs, and component specs directly from live rendered website DOMs via Manavarya09/design-extract (designlang).
metadata:
  version: "1.0.0"
  category: design_frontend
  triggers: design-extract, designlang, extract design tokens, website to tailwind, scrape design system
---

# Design Extract (designlang) — Live DOM to Design Tokens

A command-line tool and MCP server that extracts complete design systems from rendered web pages with a single command.

## Extracted Outputs
- **W3C Design Tokens (DTCG)**: Colors, typography, spacing, shadows, radii.
- **Tailwind v3/v4 Theme Config**: Ready-to-paste `@theme` directives.
- **Figma Variables & Tokens**: JSON token sets compatible with Tokens Studio.
- **Native Emitters**: Swift, Kotlin, and Flutter style files.

## CLI Usage
```bash
npx design-extract https://stripe.com --output ./design-tokens.json
```
