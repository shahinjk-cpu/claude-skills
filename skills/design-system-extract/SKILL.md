---
name: design-system-extract
description: Extract design tokens — color, typography, spacing, radii, shadows, motion, breakpoints — from a codebase, brand guide or screenshots into a tokens file in the project's own format (CSS variables, Tailwind theme, TypeScript or DTCG JSON), and report where the product disagrees with itself. Use when a project has no tokens yet, when asked to "extract tokens" or "build a design system from the code", or before measuring design-system adoption.
---

# Design System Extract

Most products already have a design system, scattered across dozens of files as hex codes and pixel values. This skill collects what's actually in use, names it, writes it to a tokens file, and shows where the product is inconsistent. The result is the baseline that `design-system-adoption` measures against.

## Phase 1: Identify sources

In a codebase, read the theme files (`theme.ts`, `tokens.*`, `_variables.scss`, `tailwind.config.*`, CSS `@theme` blocks, `:root` custom properties), the component library, and the global stylesheet. Then sample real usage: search the components for color literals (hex, `rgb`, `hsl`, `oklch`) and `px`/`rem` values, and rank them by frequency.

Other sources: a brand guide, screenshots, a design-tool export. If none is available and the codebase has no styling to extract from, ask — invented tokens defeat the purpose.

## Phase 2: Extract by category

Capture concrete values with their usage counts. Frequency tells you which value is canonical and which is drift.

- **Color** — brand (primary, accent), semantic (success, warning, error, info), neutral scale, surfaces (background, surface, border, overlay), text colors, and dark-mode values when present.
- **Typography** — families with fallback stacks, the size scale actually used, loaded weights, line heights, letter spacing for labels, and named text styles if they exist.
- **Spacing** — the scale in use, usually on a 4 px or 8 px base.
- **Radii, shadows, borders** — the distinct values and where they're used.
- **Motion** — durations and easing curves.
- **Layout** — breakpoints, container widths, z-index layers.

## Phase 3: Consolidate

Group near-duplicates: `#2563EB`, `#2564EB` and `#2463EA` are one blue; 15 px and 16 px margins are probably one step. For each group, propose the canonical value — usually the most used, or the one already in the theme — and keep the variants as a finding. Don't merge silently: the inconsistency is information the team needs.

Name tokens by role, not value: `--color-text-muted`, not `--gray-500-ish`. Keep two layers — primitives (`--blue-600`) and semantic tokens (`--color-action-primary: var(--blue-600)`) — when the product has themes or dark mode.

## Phase 4: Write the tokens file

Match the project's stack and conventions:

- **Tailwind v4** — an `@theme` block in CSS. **Tailwind v3** — `theme.extend` in the config.
- **CSS-in-JS or TypeScript** — a typed `tokens.ts`.
- **Plain CSS** — custom properties on `:root`, with a dark block under `[data-theme="dark"]` or `prefers-color-scheme`.
- **Several platforms** — DTCG JSON (`$value`, `$type`) for a build tool such as Style Dictionary.

Group by category and comment where a value came from when it isn't obvious. Don't wire the tokens into components unless asked: that migration is what `design-system-adoption` plans.

## Phase 5: Report

Summarize: sources used, tokens per category, inconsistencies (with counts and the proposed canonical value), gaps — categories the product doesn't define, which are decisions for the team rather than values to invent — and the next step, usually `design-system-adoption` to measure how much of the codebase uses these tokens.
