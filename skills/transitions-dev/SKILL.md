---
name: transitions-dev
description: >
  Modern CSS View Transitions and fluid layout choreography from Transitions.dev. Page transitions, shared element morphing, and smooth React/Next.js page swaps.
metadata:
  version: "1.0.0"
  category: design_frontend
  triggers: transitions.dev, view transitions, page transitions, shared element transition, fluid motion
---

# Transitions.dev — Fluid View Transitions & Motion

Implements native browser View Transitions API and CSS choreography for instantaneous, app-like navigation and shared element morphs.

## CSS View Transitions Snippet
```css
@view-transition {
  navigation: auto;
}

::view-transition-old(root) {
  animation: fade-out 0.25s ease-out both;
}

::view-transition-new(root) {
  animation: fade-in 0.25s ease-in both;
}
```
