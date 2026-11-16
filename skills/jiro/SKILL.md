---
name: jiro
description: Vibe-coding & Landing Page MCP skill. Connects to Jiro Build (https://mcp.jiro.build) to retrieve pre-built, production-ready React/Tailwind landing page sections, high-converting hero blocks, feature grids, pricing tables, and CTA components.
metadata:
  version: "1.0.0"
  role: landing_page_architect
  transport: http
  url: https://mcp.jiro.build
  triggers: jiro, jiro build, landing page, cta bloku, pricing cədvəli, vibe coding, react komponenti, modern sayt
---

# Jiro Build — Vibe-Coding & Landing Page Component MCP Skill

Jiro Build is an MCP server providing instant access to production-ready React and Tailwind CSS sections designed specifically for high-conversion landing pages, startup homepages, and vibe-coding workflows.

## When to Use

Activate this skill when:
- Bootstrapping or refining a SaaS landing page, portfolio, or product launch site.
- The user requests structured, polished sections (e.g. Hero section, Social Proof, Bento Feature Grid, Pricing Tier matrix, FAQ accordion, Testimonial carousel, or Call-to-Action block).
- Aiming for crisp, clean Tailwind styling with proper spacing, typography hierarchy, and dark mode support.

## Architecture & MCP Integration

- **MCP Server Name:** `jiro`
- **Endpoint:** `https://mcp.jiro.build`
- **Transport:** Streamable HTTP
- **Authentication:** OAuth via Supabase (`claude mcp login jiro` / `mcporter auth jiro`)

## Workflow for AI Agents

1. **Section Selection:**
   - Call the `jiro` MCP tools to query available section templates matching the project's brand and structure.
2. **Contextual Adaptation:**
   - Adapt copy, branding tokens (colors, font-family), and iconography to match the user's specific product or concept.
3. **Clean Code Generation:**
   - Output production-grade JSX/TSX with Lucide icons and Tailwind CSS classes.
   - Ensure semantic HTML, proper mobile responsiveness, and zero unnecessary bloat.
