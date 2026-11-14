---
name: designresources
description: Curated Design Tools & Systems MCP skill. Connects to the local designresourc.es MCP server (C:\Claude\designresources\server.py) to search 300+ hand-curated prototyping tools, production design systems (Geist, Polaris, Primer), icons, typography, and UI inspiration.
metadata:
  version: "1.0.0"
  role: design_systems_curator
  transport: stdio
  command: python C:\Claude\designresources\server.py
  triggers: designresources, design resources, dizayn alətləri, design systems, ikonlar, prototip alətləri, ui ilham, mobbin, figma
---

# Design Resources — Curated Design Tools & Systems MCP Skill

Connects directly to the `designresources` MCP server, tapping into 300+ hand-reviewed tools, production design systems, asset libraries, and inspiration sources curated by `designresourc.es`.

## Available MCP Tools

1. **`get_design_categories`**:
   - Returns all top-level design categories: Prototyping tools, AI tools for designers, Production design systems, Icons & visual assets, UI inspiration directories, and Typography.
2. **`get_category_resources(category)`**:
   - Fetches full curated entries under a category slug (e.g. `prototyping-tools`, `ai-tools-for-designers`, `design-systems-in-production`, `icons-illustrations-assets`, `ui-inspiration-that-doesnt-suck`).
3. **`search_design_resources(query, category?)`**:
   - Live search across tool names, descriptions, and categories with keywords (e.g. `figma`, `3d`, `spline`, `lucide`, `shader`, `landing`).

## When to Use

Activate this skill when:
- Exploring or recommending the best tools or component libraries for a new frontend stack.
- Looking up production design systems (Vercel Geist, Shopify Polaris, GitHub Primer, Radix, shadcn/ui) to follow best industry practices.
- Sourcing icon sets (Lucide, Phosphor, Heroicons) or typography pairings for a design sprint.
