---
name: design-aesthetic-suite
description: >
  Modern high-end interface design: Nothing OS minimalist typography, real-world non-AI web aesthetics, industrial brutalism, and retro pixel art styling.
category: design_frontend
version: "2.0.0"
role: consolidated_suite
triggers: design-aesthetic-suite, avant-garde ui & real-world web aesthetic suite, gyos-grow-your-own-software-, industrial-brutalist-ui, minimalist-ui, nothing-design-skill, pixelfx-skill, real-site-design
---

# 💎 Avant-Garde UI & Real-World Web Aesthetic Suite

Modern high-end interface design: Nothing OS minimalist typography, real-world non-AI web aesthetics, industrial brutalism, and retro pixel art styling.

This is an **Automated Consolidated Modular Suite**. Rather than cluttering the catalog with dozens of separate micro-skills, this suite centralizes all related domain knowledge while keeping context and token costs minimal.

---

## 📚 Included Sub-Modules (6 Modules)

The following capabilities and domain modules are fully integrated into this suite:

- **`gyos-grow-your-own-software-`**: Get Your Own Software. A set of Claude Code skills for knowledge-driven development. A Socratic interview turns your product idea into bounded contexts. Each context becomes a module owned by its own
  - *Reference File:* `references/gyos-grow-your-own-software-.md`
- **`industrial-brutalist-ui`**: Raw mechanical interfaces fusing Swiss typographic print with military terminal aesthetics. Rigid grids, extreme type scale contrast, utilitarian color, analog degradation effects. For data-heavy dashboards, portfolios, or editorial sites that need to feel like declassified blueprints.
  - *Reference File:* `references/industrial-brutalist-ui.md`
- **`minimalist-ui`**: Clean editorial-style interfaces. Warm monochrome palette, typographic contrast, flat bento grids, muted pastels. No gradients, no heavy shadows.
  - *Reference File:* `references/minimalist-ui.md`
- **`nothing-design-skill`**: This skill should be used when the user explicitly says "Nothing style", "Nothing design", "/nothing-design", or directly asks to use/apply the Nothing design system. NEVER trigger automatically for generic UI or design tasks.
  - *Reference File:* `references/nothing-design-skill.md`
- **`pixelfx-skill`**: Make pixel art effects and sprite animations in code with the pixelfx library, which has 244 ready-made ones, acted out by a character who winds up, freezes on contact and recovers (fire, explosions, water, ice, lightning, sci-fi, melee, impacts, projectiles, spawn and death, arcane, holy, shadow, status, nature, weather, UI, pickups, transitions, critters) to drop into a game, recolor, export as sprite sheets or remix, plus a draft, render, look, refine loop that makes new ones look hand-animated. Use when someone wants pixel art VFX, sprite animations or sprite sheets, game juice, a specific effect ("a frost nova for my mage", "a coin pickup sparkle"), wants to use or export a pixelfx effect in Godot, Unity, Phaser or a canvas game, or wants their pixel effects to look better.
  - *Reference File:* `references/pixelfx-skill.md`
- **`real-site-design`**: Design or redesign a website, homepage or landing page so it does not look AI-generated. Use before any site or landing page design, redesign, "make it look better", "it looks AI-generated", "it looks like AI slop", "make it not look like Claude", or when asked for design directions or mockups. Measure real sites in the same category, design inside their numbers, then check the result against a list of measurable AI-design fingerprints.
  - *Reference File:* `references/real-site-design.md`

---

## 🎯 How the Agent Uses This Suite

1. **Selective Context Loading (Token Economical)**:
   - When a specific sub-task is requested (e.g. `gyos-grow-your-own-software-`), do NOT read the entire suite.
   - Use `read_file` to inspect only the required reference document under `references/<submodule>.md`.

2. **Cross-Module Synergy**:
   - If a project requires multiple aspects (e.g., both 2D movement and physics, or both SQLi and XSS testing), the agent can consult the corresponding reference files seamlessly without losing context or requiring separate skill invocations.
