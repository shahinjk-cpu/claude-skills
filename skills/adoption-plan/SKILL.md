---
name: adoption-plan
description: Plan how users will discover, try, activate and keep using a feature — map entry points against the moments users need it, define the adoption funnel and the value moment, design empty states and onboarding, plan launch communication, and diagnose low adoption after launch. Use when launching or relaunching a feature, when a shipped feature is under-used, or when asked about discoverability, onboarding, activation or feature adoption.
---

# Adoption Plan

Shipping a feature isn't the same as users having it. Most under-used features aren't bad: they're invisible at the moment users need them, or they ask for effort before giving any value. This skill plans the path from "it exists" to "people use it every week", and gives a diagnosis when the numbers disappoint.

## Phase 1: Define eligible users and the value moment

Take these from `brief.md` in the feature folder (`docs/product/<feature-slug>/`) when it exists; otherwise ask:

- **Eligible users** — who should use this (role, plan, platform, the data they need). Adoption rates only mean something against this denominator, never against all users.
- **Value moment** — the first action that delivers the promised value. "Opened the invoices page" isn't one; "sent a first invoice" is. If the team can't name it, stop and agree on it first: everything below depends on it.
- **Expected frequency** — daily, weekly, monthly or once. It defines what "retained" means.

## Phase 2: Define the funnel

| Stage | Definition | Metric |
|---|---|---|
| Exposed | An eligible user saw an entry point | reach = exposed ÷ eligible |
| Tried | Started the feature once | trial rate = tried ÷ exposed |
| Activated | Reached the value moment | activation rate = activated ÷ tried; time to first value |
| Repeated | Did it again within the expected frequency window | repeat rate |
| Retained | Still using it N periods later | retention at week 4, or month 3 |

Name the event behind each stage. When an event doesn't exist yet, list it for `instrument-feature`.

## Phase 3: Audit discoverability

List every entry point in the code: navigation items, buttons and links in context, empty states, command palette, settings, notifications, emails, onboarding checklists, changelog. For each: where it lives, how many clicks it is from the usual landing screen, whether it's visible without scrolling, and who sees it (permissions, flags).

Then list the **moments of need**: the places in the product where users run into the problem the feature solves ("after exporting a CSV to build an invoice by hand"). The gap between moments of need and entry points is usually the whole adoption problem. Propose contextual entry points exactly there.

## Phase 4: Design activation

Cut what the user must do before the value moment:

- **Empty states** that explain what will appear and offer the primary action, with a template, sample data or an import where it helps.
- **Smart defaults** so the first use works with minimal setup; move configuration after the first success.
- **A short path** — run `happy-path-audit` from entry point to value moment and set its budget.
- **Guidance at the moment of need** — one contextual hint on first encounter beats a product tour at login. Tours get skipped; hints in context get read.
- **A checklist** for features with several setup steps, with progress saved.

## Phase 5: Design repeat use

- **Trigger** — what brings users back at the right time: their own workflow, a notification about something they care about (not "you haven't used X lately"), a reminder they chose.
- **Embedding** — put the feature inside workflows people already have instead of a separate destination.
- **Accumulated value** — saved state, history and templates that make the second use faster than the first.

## Phase 6: Plan launch communication

Targeted, in context, and proportional to the feature: an in-app announcement shown to eligible users at the moment of need, a changelog entry, an email only for features that change how people work, and sales and support briefings for B2B. Avoid modal announcements at login: they interrupt what the user came to do and get dismissed unread.

## Phase 7: Set targets and review dates

For each funnel stage: the baseline (from a comparable feature, if any), the target, and when to look — typically two weeks after launch for exposure and trial, six to eight weeks for retention. Agree in advance on what you'll do if a target is missed; `launch-review` runs this check at the review date.

## Diagnosing low adoption after launch

Find the first stage with a sharp drop and work on that stage only:

| Drop at | Likely cause | Next step |
|---|---|---|
| Exposed | Entry points invisible or in the wrong place | Contextual entry points at moments of need; check permissions and flags |
| Tried | The value isn't clear from the entry point | Rewrite the entry point around the outcome, and test it (`ab-test-design`) |
| Activated | Too much friction before value | `happy-path-audit` and `unhappy-paths` on the activation path; watch five users try it (`usability-test-plan`) |
| Repeated | No trigger, or the value is one-off | Add a trigger, or check whether repeat use is expected at all |
| Retained | The value fades, or a better alternative exists | Interview users who stopped using it (`user-interviews`) |

## Output

Write `adoption-plan.md` to the feature folder: eligible users, value moment, funnel with events and targets, entry-point map with proposed additions, activation and repeat-use changes, communication plan, and review dates. Summarize the biggest adoption risk and the three changes with the most impact.
