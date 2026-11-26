---
name: html-animated-presentations
description: >-
  Creates interactive, animation-rich HTML/CSS/JS slide decks and programmatic video
  presentations that run directly in any browser. Inspired by zarazhangrui/frontend-slides
  and remotion. Use when creating modern pitch decks, conference talks, or converting PPTX to web slides.
---

# HTML & Web-Native Animated Presentations

Inspired by `zarazhangrui/frontend-slides` and `remotion-dev/remotion`. Creates stunning web presentations that beat static PowerPoint slides.

## 1. Key Presentation Principles
1. **Keyboard-Driven Navigation**:
   - Arrow keys (`Left` / `Right` / `Space`), full-screen toggle (`F`), slide overview grid (`O` or `Esc`).
2. **Modern Web Presentation Stack**:
   - Single-file standalone HTML with embedded Tailwind/CSS and minimal vanilla JS, or modular frameworks like **Reveal.js** or **Sli.dev**.
3. **Motion & Transitions**:
   - Use smooth CSS transitions (`transform`, `opacity`) or GSAP for entrance/exit animations.
   - Support dark/light mode toggle and responsive scaling on projectors and laptops.
4. **Export Capabilities**:
   - Support print-to-PDF (`window.print()` with `@media print { .slide { page-break-after: always; } }`) so slides can be saved as PDF with one shortcut.
