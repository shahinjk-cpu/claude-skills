---
name: presentation-deck-suite
description: >
  Enterprise presentation suite covering PowerPoint (pptx, python-pptx, Playwright), HTML slide decks, Keynote exports, Nanobanana AI PPT, editorial canvas layouts (Guizang, Swiss, OpenSlide), and executive deck design.
category: content_media
version: "2.0.0"
role: consolidated_suite
triggers: presentation-deck-suite, master presentation & deck engineering suite, carousel-engine, deck-guizang-editorial, deck-open-slide-canvas, deck-swiss-international, frontend-slides, html-ppt-retro-quarterly-review, nanobanana-ppt, ppt-keynote, ppt-master, pptx-builder-skill, pptx-generator, pptx, slides, verifiable-editorial-skills
---

# 📊 Master Presentation & Deck Engineering Suite

Enterprise presentation suite covering PowerPoint (pptx, python-pptx, Playwright), HTML slide decks, Keynote exports, Nanobanana AI PPT, editorial canvas layouts (Guizang, Swiss, OpenSlide), and executive deck design.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (14 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`carousel-engine`**: Turn a carousel script plus messy screenshots into finished Instagram/LinkedIn carousel slides (1080x1350 PNGs, a PDF and a contact sheet) in the user's brand fonts and colours. Use when the user says "make a carousel", drops a script with "Slide 1, Slide 2...", or hands over screenshots for slides. Also use when they ask to set up, install or check the carousel engine, or to start a new carousel.
  - *Reference File:* `references/carousel-engine.md`
- **`deck-guizang-editorial`**: Editorial magazine meets e-ink: 10 layouts and 5 palettes (Ink, Indigo Porcelain, Forest Ink, Kraft Paper, Dune).
  - *Reference File:* `references/deck-guizang-editorial.md`
- **`deck-open-slide-canvas`**: Locked 1920x1080 canvas deck with React component-level free composition, not bound to a fixed template.
  - *Reference File:* `references/deck-open-slide-canvas.md`
- **`deck-swiss-international`**: 16-column grid, one saturated accent, and 22 locked layouts (Klein Blue, Lemon, Mint, Safety Orange).
  - *Reference File:* `references/deck-swiss-international.md`
- **`frontend-slides`**: Generate animation-rich HTML presentations with visual style previews. Useful for online keynotes, embedded talks, and interactive briefs.
  - *Reference File:* `references/frontend-slides.md`
- **`html-ppt-retro-quarterly-review`**: Retro Quarterly Review presentation template in a bold blue + orange editorial language. Use when users ask for a high-impact quarterly review / roadmap deck with heavyweight slab headlines, clean cream paper sections, structured grids, and fast premium motion pacing (3 slides, each hold under 3s in video mode).
  - *Reference File:* `references/html-ppt-retro-quarterly-review.md`
- **`nanobanana-ppt`**: AI-powered PPT generation with document analysis and styled images via the NanoBanana stack. Combines image generation with structured deck output.
  - *Reference File:* `references/nanobanana-ppt.md`
- **`ppt-keynote`**: Apple Keynote-quality slides, one card per screen, with keyboard left/right navigation.
  - *Reference File:* `references/ppt-keynote.md`
- **`ppt-master`**: Executive presentation designer and automated PPTX generator. Creates Apple Keynote-grade decks, 16:9 widescreen layouts, typographic contrast, and data charts.
  - *Reference File:* `references/ppt-master.md`
- **`pptx`**: Read, generate, and adjust PowerPoint slides, layouts, and templates. Useful for executive decks, training material, and product reviews.
  - *Reference File:* `references/pptx.md`
- **`pptx-builder-skill`**: Use this skill to create professional, fully-editable PowerPoint (.pptx) decks. Design each slide as HTML/CSS (preview it as an Artifact to iterate visually with the user), then run the included Playwright + python-pptx pipeline to convert the HTML into native, editable PowerPoint objects (rectangles, text boxes, images, icons, tables, lines) at pixel-accurate positions — not a screenshot dump. Trigger on "make a powerpoint", "build a pptx", "create slides", "presentation deck", "slide design".
  - *Reference File:* `references/pptx-builder-skill.md`
- **`pptx-generator`**: Create and edit PowerPoint presentations from scratch with PptxGenJS — MiniMax's production-tested deck pipeline.
  - *Reference File:* `references/pptx-generator.md`
- **`slides`**: Create and edit .pptx presentation decks with PptxGenJS. Useful for sales decks, kickoff briefs, and design-system showcases.
  - *Reference File:* `references/slides.md`
- **`verifiable-editorial-skills`**: - Operational layout formulas, typographic hierarchy, and modular grid archetypes for high-density, publication-grade institutional reports (Letter portrait) and executive slide decks (16:9 widescreen). Enforces vertical fill budgeting (85-92% Letter, 72-88% 16:9), asymmetric grids, hairline scaffolding, and zero empty-page voids.
  - *Reference File:* `references/verifiable-editorial-skills.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `carousel-engine`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
