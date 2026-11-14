---
name: motionsites
description: Cinematic & 3D Website MCP skill. Connects to MotionSites AI (https://motionsites.ai/api/mcp) to build high-end animated websites, cinematic SaaS landing pages, smooth scroll experiences, and creative portfolio layouts.
metadata:
  version: "1.0.0"
  role: cinematic_web_director
  transport: http
  url: https://motionsites.ai/api/mcp
  triggers: motionsites, motionsite, kinematoqrafik sayt, 3d sayt, smooth scroll, lüks dizayn, portfolio səhifəsi
---

# MotionSites AI — Cinematic & 3D Web Experience MCP Skill

MotionSites AI provides award-winning, cinematic website architectures, fluid motion patterns, and 3D visual layouts to elevate AI-generated web apps beyond generic flat interfaces.

## When to Use

Activate this skill when:
- Designing a high-impact creative portfolio, luxury agency website, or next-generation tech showcase.
- The user requests smooth scrolling (Lenis/Locomotive), parallax depth, dynamic pinned sections, or continuous canvas storytelling.
- Building immersive dark-mode interfaces with cinematic typography and atmospheric lighting.

## Architecture & MCP Integration

- **MCP Server Name:** `motionsites`
- **Endpoint:** `https://motionsites.ai/api/mcp`
- **Transport:** Streamable HTTP
- **Authentication:** OAuth via Supabase (`claude mcp login motionsites` / `mcporter auth motionsites`)

## Workflow for AI Agents

1. **Retrieve Motion Patterns:**
   - Query `motionsites` MCP tools for curated layout blueprints, scroll animations, and transition choreographies.
2. **Implement Motion Architecture:**
   - Configure framer-motion variants, GSAP ScrollTrigger timelines, or CSS View Transitions API.
   - Respect user accessibility preferences (`prefers-reduced-motion: reduce`).
3. **Harmonize Visual Polish:**
   - Pair with `taste` and `transition` skills for flawless color temperature, timing curves, and typography scale.
