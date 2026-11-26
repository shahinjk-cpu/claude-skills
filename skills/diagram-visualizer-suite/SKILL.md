---
name: diagram-visualizer-suite
description: >
  Architecture and flow diagramming suite: Excalidraw real-time programmatic canvas sync, Draw.io, Mermaid conversion, stack diagrams, diagram animations, and visual concept whiteboards.
category: design_frontend
version: "2.0.0"
role: consolidated_suite
triggers: diagram-visualizer-suite, master diagram & visual architecture suite, diagram, diagram-animation, diagram-design, diagram-maker, diagram, drawio-skill, mcp-excalidraw, pastel-diagrams, stack-diagram
---

# 📐 Master Diagram & Visual Architecture Suite

Architecture and flow diagramming suite: Excalidraw real-time programmatic canvas sync, Draw.io, Mermaid conversion, stack diagrams, diagram animations, and visual concept whiteboards.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (8 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`diagram`**: Turn an English description (or mermaid source) into a diagram triplet: the source, an editable .excalidraw file you can open (gstack)
  - *Reference File:* `references/diagram.md`
- **`diagram-animation`**: This skill should be used when the user asks to "animate this diagram", "build a flowchart that reveals step by step", "animate an architecture/sequence diagram", "make a chart animate in", "grow the bars / draw the line / count up the number", "show data flowing along a connector", or "turn a static diagram into a guided reveal". Covers SVG, Framer Motion, D3, and Remotion.
  - *Reference File:* `references/diagram-animation.md`
- **`diagram-design`**: Create branded architecture, architecture delta, IT current-state, flowchart, sequence, state machine, ER/data model, steps, timeline, swimlane, quadrant, radar/spider, polar chart (polar/radial lollipop), loop/flywheel, nested, tree, org chart, layer stack, exploded axonometric, axonometric plan, Venn, pyramid/funnel, treemap and marimekko, unit grid, heatmap, bar and dumbbell, waterfall, line (slopegraph, ridgeline, streamgraph, bump), Gantt and scatter charts (bubble, beeswarm, box plot), high-level, process, medallion, data flow, DP integration, DP security matrix, Sankey, fishbone, Wardley map, kanban, user journey, service blueprint, deployment, dependency graph (arc diagram), UML class, story map, database schema, SBGN, requirement traceability, or event modeling diagrams as HTML/SVG/PNG, with .drawio, Mermaid, .excalidraw, and PlantUML import, plus lifecycle phase maps, block decomposition trees, and onboarding guidance.
  - *Reference File:* `references/diagram-design.md`
- **`diagram-maker`**: Create SVG/HTML or Excalidraw diagrams for concepts, architecture, flows, and whiteboards.
  - *Reference File:* `references/diagram-maker.md`
- **`drawio-skill`**: Create and edit draw.io/diagrams.net diagrams as editable `.drawio` files. Covers architecture, UML/ERD/sequence, BPMN, network, and swimlane views authored from a description or converted from code, IaC, SQL, and API schemas, plus sync, query, test, review, export, and publish of existing diagrams. Use when the user asks for draw.io/diagrams.net or an editable diagram; prefer Mermaid/PlantUML when diagrams-as-code is enough.
  - *Reference File:* `references/drawio-skill.md`
- **`mcp-excalidraw`**: Excalidraw canvas toolkit for creating, editing, and refining diagrams on a live canvas. Use when an agent needs to (1) draw or lay out diagrams, (2) iteratively refine them by describing the scene and screenshotting its own work, (3) export/import .excalidraw files or PNG/SVG images, (4) save/restore canvas snapshots, (5) convert Mermaid to Excalidraw, or (6) perform element-level CRUD, alignment, distribution, grouping, duplication, and locking. Primary interface is the bundled CLI (npx -y mcp-excalidraw-server <command>) which auto-starts the canvas server; MCP tools and a REST API are equivalent alternatives.
  - *Reference File:* `references/mcp-excalidraw.md`
- **`pastel-diagrams`**: Draw clean, modern diagrams (flowcharts, architecture, process and status flows, state machines, sequence, ER/data model, timeline and mindmap diagrams) in a soft pastel whiteboard style — rounded cards, Inter font, Lucide icons, straight rounded-corner connectors that attach to card side centres, light or dark themes, sticky-note comments and emoji stickers — and export them as SVG, 3x PNG, a self-contained HTML page and a light/dark auto-switching SVG. Also renders ```mermaid blocks in Markdown files to images. Use when the user asks for a diagram, flowchart, architecture diagram, user flow, process map, status lifecycle, state diagram, data model, sequence diagram, timeline or mindmap for docs, READMEs, slides or guides, wants review comments or stickers on a diagram, or says a diagram looks dated or plain.
  - *Reference File:* `references/pastel-diagrams.md`
- **`stack-diagram`**: Create cloud-architecture-style diagrams of tech stacks, system architectures, infra layouts, and service topologies — with real brand logos, grouped containers, and clean orthogonal arrows — delivered as self-contained HTML, a PNG image, a React/TSX component, or a live artifact. Use this skill whenever the user asks for an architecture / system / stack / infra diagram, a tech-stack overview, a service topology, a cloud-vendor-style diagram, or wants tech logos arranged into a picture of how their services connect — in any language, even if they don't name an output format, and even if the tools involved aren't cloud services.
  - *Reference File:* `references/stack-diagram.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `diagram-animation`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
