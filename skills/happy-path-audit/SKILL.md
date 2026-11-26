---
name: happy-path-audit
description: Count what it costs a user to finish a task — clicks, fields, characters typed, screens, decisions, waits — by tracing the flow through the real code, estimate task time with the Keystroke-Level Model, and propose ranked reductions with their savings and a click budget. Use when asked "how many clicks does it take to…", to audit or simplify a flow, onboarding, checkout or form, or to compare two versions of a flow.
---

# Happy Path Audit

Measure the cheapest route from a start state to a goal state, step by step, and find what to cut. Users don't experience your architecture; they experience the decisions, fields and waits between them and the result. Counting makes that cost visible and comparable.

## Phase 1: Define the task

Take it from `brief.md` in the feature folder (`docs/product/<feature-slug>/`) when it exists; otherwise ask:

- **Start state** — where the user is and what's true ("logged-in admin on the dashboard, no invoices yet").
- **Goal state** — the observable result ("invoice sent, confirmation visible").
- **Persona** — first-time and returning users often take different paths (onboarding, empty states, remembered choices). Audit the one asked for; if unclear, audit first-time and note where returning users differ.
- **Platform** — mouse, touch or keyboard-first. It changes the cost model.

## Phase 2: Trace the path through the code

Find the entry points first: routes, navigation items, buttons and links, deep links from emails or notifications, command-palette entries. Pick the one a typical user takes from the start state. The shortest path isn't always the typical one; note both if they differ.

Then follow the flow: route → page component → interactive elements → event handlers → API calls → redirects, modals, toasts. On each screen, record what the user must read, decide, type and click to move on. Read validation rules (required fields, formats), conditional branches, default values and loading states — they all change the count.

If the app runs locally and you have browser automation, walk the path for real afterwards and correct the trace. Tag every number with its source:

- **Measured** — observed by running the app or a test.
- **Traced** — derived from reading the code.
- **Estimated** — inferred where the code was ambiguous; say why.

## Phase 3: Record every step

One row per user action:

| # | Screen / route | Action | KLM operators | Typed | Wait | Decision | Notes |
|---|---|---|---|---|---|---|---|
| 1 | /dashboard | Click "New invoice" | M P BB | — | route change | — | Button below the fold on a 13" screen |
| 2 | /invoices/new | Pick client from dropdown | M P BB, M P BB | — | client list fetch | Which client | No search; 40 clients in seed data |
| 3 | /invoices/new | Fill amount | M P BB H K×6 | 6 chars | — | — | No default currency |

Then total:

- **Clicks** — activations of controls: buttons, links, menu items, options, checkboxes, tabs, including opening dropdowns and closing modals. Focusing a text field is part of filling it, not a separate click.
- **Fields** — inputs the user fills, and **characters typed** (use realistic lengths: email ≈ 20, name ≈ 12, amount ≈ 6).
- **Screens** — route changes and modals.
- **Decisions** — points where the user must choose between options.
- **Waits** — network round trips that block the user.
- **Context switches** — leaving the product (checking email, copying a code from another app).
- **Scrolls** needed to reach the next control.

Use the same definitions of clicks and fields as `flow-test`, so the budget you set here can be asserted there.

## Phase 4: Estimate task time with KLM

The Keystroke-Level Model (Card, Moran and Newell) turns operators into seconds:

| Operator | Meaning | Time |
|---|---|---|
| K | Keystroke | 0.28 s for an average typist, 0.2 s for a skilled one |
| P | Point at a target with the mouse | 1.1 s |
| B | Mouse button press or release (a click is BB) | 0.1 s |
| H | Move a hand between keyboard and mouse | 0.4 s |
| M | Mental preparation | 1.35 s |
| R | System response the user waits for | measured or estimated |

Simplified placement of M: one before each decision, before starting to type into a field, and before the first action on a new screen. No M between keystrokes of the same word, or between pointing and clicking in the same move. A click on a new screen is typically `M P BB` = 2.65 s.

On touch, don't reuse the mouse values: count taps and fields, and give seconds only when you can justify the numbers (for example, from measurements).

KLM models an expert performing without errors; first-time users are slower. Use it to compare versions of the same flow, never to promise users a duration. To see where real users struggle, run `usability-test-plan`.

## Phase 5: Find reductions

Go through the step table and ask, for each step, whether it can be removed, merged, defaulted or made faster. Common levers, roughly by impact:

1. **Remove the step.** Is the screen or confirmation needed at all? Replace confirmation dialogs with undo.
2. **Default or infer.** Prefill from what the product already knows: profile, last-used value, organization settings, URL parameters, the object the user came from.
3. **Defer.** Move fields that aren't needed for the first value to later (progressive profiling).
4. **Merge.** Combine screens, edit inline instead of in a modal, create the object where the need appears.
5. **Change the input.** Selection instead of typing for short closed lists, search or autocomplete for long lists, `autocomplete="one-time-code"` for codes.
6. **Shorten the route.** Add a contextual entry point where the need arises; deep-link emails and notifications to the exact step.
7. **Remove waits.** Prefetch the next screen's data, update optimistically, run requests in parallel.
8. **Keyboard.** Autofocus the first field, submit with Enter, set the right `type` and `autocomplete` attributes.
9. **Remove context switches.** Magic links or code autofill instead of "check your email and come back".

For each proposal, give savings and cost:

| Proposal | Δ clicks | Δ fields | Δ time (KLM) | Effort | Trade-off |
|---|---|---|---|---|---|

Sort by savings divided by effort. State trade-offs honestly: a default can be wrong, removing a confirmation needs a reliable undo, a merged screen can become overloaded.

## Phase 6: Set the budget

Propose a **click budget** and a **field budget** for the flow: today's totals, and the target once the recommended reductions land. `flow-test` turns them into a test that fails when the flow gets longer.

## Output

Write `flow-audit.md` to the feature folder: task definition, step table, totals, KLM estimate, reductions table, proposed budget, and the assumptions you couldn't verify.

To compare versions (before and after a redesign, `main` against a branch), produce one step table per version and a side-by-side totals table.

Summarize in the conversation: the current cost (clicks, fields, approximate seconds), the top three reductions with their savings, and the proposed budget.
