---
name: horizonx
description: Interactive UI & 3D Component MCP skill. Connects to HorizonX (https://horizonx.so/api/mcp) to search, inspect, and import animated React/WebGL components, 3D backgrounds, shaders, and modern interactive widgets into web projects.
metadata:
  version: "1.0.0"
  role: frontend_designer
  transport: http
  url: https://horizonx.so/api/mcp
  triggers: horizonx, animasiyali komponent, 3d background, shader, webgl, animativ vidcet, interaktiv duyme
---

# HorizonX — Animated UI & Shader MCP Skill

HorizonX is a specialized design-engineering Model Context Protocol (MCP) server that empowers AI agents to search, inspect, and seamlessly import high-end animated UI components, WebGL shaders, 3D backgrounds, and interactive elements into web projects.

## When to Use

Activate this skill when:
- Creating or polishing modern frontend web apps (React, Next.js, Svelte, Vue, or HTML/Tailwind).
- The user asks for animated or interactive elements (e.g. glowing buttons, floating cards, particles, ray-marched canvas, fluid distortions).
- Building modern hero sections that need animated 3D or WebGL visual depth.
- Implementing micro-interactions that elevate visual fidelity beyond standard CSS.

## Architecture & MCP Integration

- **MCP Server Name:** `horizonx`
- **Endpoint:** `https://horizonx.so/api/mcp`
- **Transport:** Streamable HTTP
- **Authentication:** OAuth (`claude mcp login horizonx` / `mcporter auth horizonx`)

## Workflow for AI Agents

1. **Query HorizonX Library:**
   - Search for the required visual element (e.g. `animated-hero-mesh`, `glow-card`, `glass-slider`, `particle-field`).
2. **Inspect Component Structure:**
   - Review component props, dependencies (e.g. `three`, `framer-motion`, `@react-three/fiber`), and styling requirements.
3. **Integrate into Project:**
   - Install necessary peer dependencies cleanly.
   - Insert the component code into the project's component tree.
   - Verify responsive layout, performance, and accessibility (reduced motion support).
