---
name: getlayers
description: GetLayers AI & Figma-to-Code MCP skill. Connects to GetLayers (https://mcp.getlayers.ai/mcp) and the GetLayers Figma plugin to import editable non-generic web templates, live-tuned shaders, gradients, 3D WebGL scenes, and Next.js motion layouts directly into web projects.
metadata:
  version: "1.0.0"
  role: figma_to_code_architect
  transport: http
  url: https://mcp.getlayers.ai/mcp
  triggers: getlayers, getlayers ai, figma to code, getlayers figma, 3d scenes, live shaders, nextjs templates, non generic design
---

# GetLayers AI — Figma-to-Code & 3D Web MCP Skill

GetLayers AI (`getlayers.ai`) bridges visual design in **Figma** and production frontend development in **Claude Code, Cursor, and Antigravity** via its dedicated Model Context Protocol (MCP) server.

## Overview & Two-Way Pipeline

1. **Inside Figma (Figma Plugin):**
   - Install the **GetLayers** plugin from [Figma Community](https://www.figma.com/community/plugin/getlayers).
   - Drop pre-built, non-generic website templates directly onto your canvas as native Figma frames, auto-layouts, and design tokens (with responsive desktop, tablet, and mobile views).
   - Tweak live-tuned shaders, color gradients, and place 3D WebGL background scenes.

2. **Inside AI Coding Assistant (GetLayers MCP):**
   - **MCP Server Name:** `getlayers`
   - **Endpoint URL:** `https://mcp.getlayers.ai/mcp`
   - **Transport:** Streamable HTTP
   - **Authentication:** OAuth (`claude mcp login getlayers` or `mcporter auth getlayers`)
   - The coding agent queries GetLayers for section blueprints, animations, and shader configs to turn Figma frames into live, production-ready React/Next.js code.

## When to Use

Activate this skill when:
- The user provides or asks for Figma designs powered by GetLayers.
- Building cinematic landing pages that require WebGL/Three.js 3D backgrounds and dynamic gradient shaders.
- Converting Figma layout frames directly into responsive Tailwind CSS + Framer Motion components.
- Designing high-conversion startup homepages without generic "cookie-cutter" AI aesthetics.

## Coding Workflow for AI Agents

1. **Query GetLayers Assets:** Use `getlayers` MCP tools to fetch template schemas, responsive variants, and motion configs.
2. **Synchronize Figma Tokens:** Align colors, typography, and spacing with the Figma design tokens.
3. **Generate Production Code:** Scaffold clean Next.js/React components with Tailwind classes, ensuring accessibility and mobile responsiveness.
