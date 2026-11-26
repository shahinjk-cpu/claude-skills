---
name: accessibility-audit
description: Audit and fix accessibility in the product's real UI code against WCAG 2.2 AA — contrast, semantics, keyboard and focus, screen-reader names and announcements, forms and errors, motion, target size — combining the automated checks the project supports (axe, lint rules) with a manual review of what tools can't catch. Use when accessibility is questioned, before shipping user-facing UI, for a compliance review, or when ux-review flags accessibility issues.
---

# Accessibility Audit

Accessibility failures are product failures: a form a keyboard user can't submit converts at 0 % for that user. Automated tools catch only part of the problems; the rest takes reading the code and walking the flow. This skill does both, then fixes what it finds.

## Phase 1: Scope

Audit what was asked: a flow (use the steps from `flow-audit.md` in the feature folder if there is one), a set of components, a PR diff, or an area of the product. Read the components involved and the design system's base components — an accessibility bug fixed in a shared `Button` is fixed everywhere.

Target WCAG 2.2 level AA unless the user says otherwise.

## Phase 2: Run the automated checks the project supports

- **axe-core** through the existing E2E setup (`@axe-core/playwright`, `cypress-axe`) on each screen of the flow, including its states: open dialog, error state, empty state.
- **Lint rules** such as `eslint-plugin-jsx-a11y`, `eslint-plugin-vuejs-accessibility` or Angular's template accessibility rules, when configured.

Don't add a dependency without asking. When the project has none, do the manual review and recommend one tool in the summary.

## Phase 3: Review by category

If you can run subagents, run these four passes in parallel on the same files; otherwise run them one after another and finish all four before fixing. Every pass reports every issue — including uncertain and minor ones — with a severity and a confidence. Filtering happens in Phase 4.

**Pass 1 — Contrast and color**
- Text contrast at least 4.5:1, or 3:1 for large text (24 px, or 18.66 px bold). Icons, input borders and focus indicators at least 3:1 against adjacent colors. Compute ratios from resolved token values, including dark mode and hover or disabled states.
- No information carried by color alone: error borders without text, status dots without labels, charts without labels or patterns.
- Text resized to 200 % and reflow at 320 px wide without loss of content.

**Pass 2 — Structure and semantics**
- Native elements for their role: `<button>` for actions, `<a href>` for navigation, real form controls. Flag click handlers on `div` and `span` and the ARIA patches around them.
- Landmarks (`header`, `nav`, `main`), one `h1` per page, no skipped heading levels.
- Accessible names: icon-only buttons have `aria-label`; images have meaningful `alt`, or `alt=""` when decorative; link text makes sense out of context ("View invoice #1042", not "Click here").
- Custom widgets (combobox, tabs, menu, dialog) follow the ARIA Authoring Practices patterns — or, better, use the design system's accessible primitive.
- Dynamic updates are announced: toasts and async results through a live region; route changes in single-page apps move focus or announce the new page title.

**Pass 3 — Keyboard and focus**
- Every interactive element is reachable and operable with Tab, Enter, Space, Escape and the arrows its pattern requires. No positive `tabindex`.
- A visible focus indicator (`:focus-visible`), never removed without a replacement, and not hidden under sticky headers or banners.
- Dialogs keep focus inside, close on Escape, and return focus to their trigger. Opening a menu or drawer doesn't drop focus to `<body>`.
- Focus order follows reading order. After a failed submit, focus moves to the first invalid field or the error summary.

**Pass 4 — Forms, input and motion**
- Every input has a programmatic label (a placeholder is not a label); required fields are indicated in text; errors are linked with `aria-describedby` and say what to fix.
- `autocomplete`, `type` and `inputmode` set on personal-data fields; users aren't asked again for information they already gave in the same flow.
- Sign-in allows paste and password managers; no puzzle or memory test without an alternative.
- Help (contact link, chat, FAQ) sits in the same place on every screen of a flow.
- Targets at least 24 × 24 CSS px; aim for 44 × 44 on touch.
- Drag-only actions have a single-pointer alternative.
- `prefers-reduced-motion` respected for non-essential animation; nothing flashes more than three times per second.

## Phase 4: Aggregate and fix

Merge duplicates and group:

1. **Blockers** — the user can't complete the task: keyboard traps, unlabeled controls in the flow, unreachable actions, unnamed icon-only buttons, failing contrast on primary text.
2. **Serious** — possible but hard: bad focus order, unannounced errors, small targets.
3. **Moderate** — everything else.

Fix blockers and serious issues in code, in shared components where possible, then re-run the automated checks. Note false positives (third-party embeds, decorative content) and skip them with the reason.

## Output

Summarize: scope, tools run, issues by severity and category, fixes with their files, what remains and why, and one way to prevent regressions (an axe check inside the flow tests, a lint rule). Passing automated checks doesn't make a product accessible, so say which parts you reviewed by hand.
