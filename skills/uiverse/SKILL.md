---
name: uiverse
description: >
  Open-source community-built CSS and Tailwind UI element library. Copy-paste buttons, cards, checkboxes, loaders, tooltips, and inputs with striking visual designs.
metadata:
  version: "1.0.0"
  category: design_frontend
  triggers: uiverse, uiverse.io, css buttons, tailwind cards, custom loaders, ui elements
---

# UIverse — Community Open-Source CSS & Tailwind Primitives

Accesses and integrates thousands of community-crafted CSS and Tailwind UI components: glowing buttons, futuristic cards, neon checkboxes, sleek loaders, and animated toggles.

## Implementation Guidelines
- Prefer CSS custom properties for palette adaptation.
- Strip fixed pixel dimensions in favor of fluid flex/grid layouts.
- Optimize keyframe animations to utilize only `transform` and `opacity` for hardware-accelerated 60fps rendering.
