---
name: interactive-3d-sim-suite
description: >
  Interactive spatial physics & 3D visualization: machine disassembly simulation (Teardown), 2D-to-3D mesh elevation (img2threejs), and dynamic asset pipelines.
category: game_3d
version: "2.0.0"
role: consolidated_suite
triggers: interactive-3d-sim-suite, interactive 3d assembly & simulation suite, img2threejs, teardown-skill
---

# ⚙️ Interactive 3D Assembly & Simulation Suite

Interactive spatial physics & 3D visualization: machine disassembly simulation (Teardown), 2D-to-3D mesh elevation (img2threejs), and dynamic asset pipelines.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (2 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`img2threejs`**: Convert 2D images, textures, and UI mockups into interactive Three.js 3D planes, displacement meshes, and WebGL scenes with depth and lighting.
  - *Reference File:* `references/img2threejs.md`
- **`teardown-skill`**: Build an interactive 3D simulator of a real machine or mechanism (an engine, a landing gear, a walking linkage, a pump, a gearbox) as one offline HTML page people can take apart, with live panels driven by the same model that moves the parts, a button for every subsystem, cutaways, camera views and an auto tour that hands control to the visitor; then record it frame by frame to a 60 fps video with a synced procedural score. Use when someone asks how a machine works, wants a "visual explainer", a "simulator", a "cutaway", an "exploded view" or an "interactive 3D lesson", or wants a 3D object shown working rather than described.
  - *Reference File:* `references/teardown-skill.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `img2threejs`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
