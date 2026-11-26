---
name: unhappy-paths
description: Map and fix everything that can go wrong along a user flow — validation errors, server failures, empty, loading and slow states, permissions, expired sessions, double submits, refresh and back button mid-flow — and flag dead ends where the user has no way forward. Use when a flow is about to ship or has just been audited, when users report "it just spins" or "I lost my data", or when asked about edge cases or error handling in the UI.
---

# Unhappy Paths

Your team walks the happy path every day. Users also meet the other paths: the declined card, the empty list, the session that expired while they typed. This skill runs every step of a flow through a matrix of failure states, checks how the code handles each one, and fixes the gaps.

## Phase 1: Get the flow

Use the step table from `flow-audit.md` in the feature folder (`docs/product/<feature-slug>/`) when it exists. Otherwise trace the happy path first (route → component → handlers → API calls): you need the list of steps and the requests each one makes.

## Phase 2: Run the state matrix

For each step, check every state that applies:

| State | What to check in the code |
|---|---|
| **Loading** | Is there a visible loading state? Does the layout stay stable (skeleton) instead of jumping? |
| **Slow** (> 1 s, > 10 s) | Does anything say it's still working? Can the user cancel? Is there a timeout? |
| **Empty** | With zero items, does the screen say what goes here and offer the action that creates the first one? |
| **Validation error** | Is the message next to the field, specific, in the user's terms? Is input kept? Does focus move to the first error? |
| **Server error** (4xx, 5xx) | Is it caught? Does the user see what happened and a way forward (retry, contact)? Is input kept? |
| **Offline** | Does the request fail visibly, and can the user retry without retyping? |
| **Permission denied** | Does a user without rights see the entry point at all? If so, are they told why and whom to ask? |
| **Session expired** | Mid-form, does signing in again bring the user back with their input? |
| **Double submit** | Is the trigger disabled while pending? Is the server operation idempotent? |
| **Refresh, back, deep link** | Does refreshing mid-flow lose state? Does landing directly on step 3 crash or redirect sensibly? |
| **Concurrent change** | Another user or tab edited or deleted the object: is the conflict detected or silently overwritten? |
| **Disabled** | Does a disabled control say why it's disabled and what unlocks it? |
| **Limits** | Long names, translations 30–40 % longer than English, 0, exactly 1 or thousands of items, quotas reached, large files: do layout and logic hold? |
| **Partial success** | In bulk or multi-step operations, does the user learn which parts failed? |

Skip states that can't occur in this flow, with a one-line reason, rather than leaving them out silently.

## Phase 3: Classify each cell

- **Handled** — the user understands what happened and has a next action.
- **Weak** — handled, but at a cost: generic message ("Something went wrong"), input lost, error far from its field, no retry.
- **Missing** — crash, blank screen, infinite spinner, silent failure or silent success.
- **Dead end** — the user can't go forward or back without reloading or leaving. Always a blocker.

For Weak and Dead-end cells, estimate the **recovery cost**: the clicks and fields needed to get back on the happy path. A validation error that clears a twelve-field form costs twelve fields.

Record every suspected gap with a confidence level, then filter in Phase 4. Being unsure about a state is a reason to report it with low confidence, not to leave it out.

## Phase 4: Fix

Fix Missing and Dead-end cells first, then Weak ones, with the project's existing components (error banners, toasts, empty states, skeletons) rather than one-offs. Defaults when the project has no pattern:

- **Error messages** say what happened, why if known, and what to do now: "Your bank declined the card. Try another card or contact your bank." — not "Payment error".
- **Keep the input** on every error. Never clear a form the server rejected.
- **Pending actions** disable their trigger and show progress in place; re-enable on failure.
- **Empty states** say what will appear and offer the primary action that creates the first item.
- **Permissions**: hide entry points the user can never use; explain how to get access when they could.

List what you couldn't fix (server behavior out of scope, product decisions) as open items.

## Output

Write `unhappy-paths.md` to the feature folder: the matrix (steps × states, with status), recovery costs, fixes applied, and open items. List the unhappy paths important enough for an automated test, for `flow-test` to cover.

Summarize: dead ends found and fixed, weak states improved, and open items that need a product decision.
