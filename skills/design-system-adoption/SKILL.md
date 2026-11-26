---
name: design-system-adoption
description: Measure how much of a codebase actually uses its design system — token coverage versus hardcoded colors, spacing and font sizes, design-system components versus local re-implementations and forks — find the hotspots and the repeated patterns that should become components, and plan a ratcheted migration with lint rules and safe codemods. Use when asked whether the design system is used, why the UI is inconsistent, to inventory components, or to plan a design-system migration.
---

# Design System Adoption

A design system only helps where the code uses it. Teams know their design system exists; few know that a third of their colors are still hardcoded or that the product has six button implementations. This skill measures adoption the way you measure test coverage — reproducibly and per area — and turns the result into a migration plan that can't regress.

## Phase 1: Locate the system

Find the tokens (CSS custom properties, Tailwind theme, theme object, DTCG files) and the component library: an internal package or folder, or an external one (MUI, Chakra, Mantine, Radix, shadcn/ui, Ant Design, Polaris…). Note which components it provides and how they're imported. If there are no tokens yet, run `design-system-extract` first.

Scope the measurement to application source. Exclude the design system's own code, generated files, vendored code, tests, stories and fixtures.

## Phase 2: Measure token adoption

For each category, count token usages against hardcoded values in the scoped files, using commands someone else can re-run. Example patterns to adapt to the stack (use ripgrep when available):

| Category | Hardcoded | Token usage |
|---|---|---|
| Color | `#[0-9a-fA-F]{3,8}\b`, `rgba?\(`, `hsla?\(`, `oklch\(` in styles; Tailwind arbitrary values like `bg-[#…]` | `var(--color-…)`, theme references, Tailwind classes from the theme palette |
| Spacing | `margin`, `padding`, `gap` with `px` values off the scale; Tailwind `p-[13px]` | scale classes, `var(--space-…)` |
| Font size | `font-size:` literals, Tailwind `text-[15px]` | type-scale classes or tokens |
| Radius, shadow, z-index | literals in those properties | tokens |

Report **adoption = token usages ÷ (token usages + hardcoded values)** per category and per top-level area (feature folder, package or route). Count separately the literals that exactly equal a token value: they're the easy wins.

Expect noise. SVG fills, third-party overrides and one-off illustrations are legitimate. Review a sample of matches for each pattern and state the estimated false-positive rate instead of presenting the number as exact.

## Phase 3: Measure component adoption

For each design-system component, count:

- **DS usages** — imports from the design system.
- **Native re-implementations** — raw `<button>`, `<input>`, `<select>`, `<dialog>` and similar elements styled locally where a DS component exists.
- **Local look-alikes** — components outside the system whose name or markup duplicates one (`PrimaryButton`, `MyModal`, `CardV2`).
- **Forks** — copies of a DS component modified locally.

Report **component adoption = DS usages ÷ (DS usages + re-implementations + look-alikes)** per component.

## Phase 4: Find candidates for new components

Look for UI patterns that appear at least three times without a DS component: cards, list rows, empty states, page headers, stat tiles, form sections. For each candidate, list the variants and states actually used (default, hover, focus, disabled, loading, error), the tokens it should use, and its accessibility requirements — enough for someone to build it once.

## Phase 5: Plan the migration

Prioritize by **frequency × visibility ÷ effort**: a hardcoded color on every screen of the main flow beats 30 occurrences in an admin page.

1. **Safe codemods** — literals that exactly equal a token value can be replaced automatically. Propose the script and apply it only if asked, in its own commit.
2. **Manual replacements** — near-values and local components, grouped into PR-sized batches by area, in priority order.
3. **New components** from Phase 4.
4. **Stop the regression.** Add a lint rule that forbids new hardcoded values in the scoped files — stylelint (`color-no-hex`, `declaration-property-value-disallowed-list`), an ESLint rule on Tailwind arbitrary values, or restricted imports for deprecated components — with a baseline of existing violations or warnings-only on old code, so the rule can land today. Ratchet: the count can go down, never up.

## Output

Write `docs/product/design-system-adoption.md` (or the project's docs location) with: the commands used, adoption per category and per area, the component adoption table, hotspots (top files and areas), candidate components with their inventory, and the migration plan. Summarize the headline numbers and the three changes with the best impact-to-effort ratio. Re-running the same commands later shows the trend.
