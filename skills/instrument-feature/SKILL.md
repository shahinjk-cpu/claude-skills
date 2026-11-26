---
name: instrument-feature
description: Design and implement product analytics for a feature — a tracking plan with event names, properties and funnel definitions, wired into the analytics tool the project already uses (PostHog, Amplitude, Segment, Mixpanel, GA4, RudderStack, Snowplow or an in-house wrapper), then verified to fire once with the right data. Use when a feature needs metrics, when asked to add tracking, analytics or events, or when a brief, adoption plan or A/B test needs events that don't exist yet.
---

# Instrument Feature

You can't improve what you can't see, and you can't trust data that was tracked carelessly. This skill writes a small tracking plan tied to the questions the team needs answered, implements it with the project's existing tools and conventions, and checks that it works.

## Phase 1: Find the analytics setup

Search the codebase for the tracking layer: SDK calls (`posthog.capture`, `amplitude.track`, `analytics.track`, `mixpanel.track`, `gtag('event'`, `rudderanalytics.track`, Snowplow trackers), server-side SDKs, and above all the project's own wrapper (a `track()` helper, a `useAnalytics` hook, an `events.ts` file). If there's a wrapper, always go through it.

Read 10 to 20 existing events to learn the conventions: naming style (`Invoice Sent`, `invoice_sent`, `invoice:sent`), standard properties, how user and account identity are set (`identify`, `group`), and where events are typed or documented.

If the project has no analytics at all, stop and ask which tool to use. Adding a tracking vendor is a product, legal and privacy decision.

## Phase 2: Start from the questions

List the questions the data must answer, from `brief.md`, `adoption-plan.md` and `experiment.md` in the feature folder (`docs/product/<feature-slug>/`) when they exist:

- The primary and guardrail metrics from the brief
- Each funnel stage from the adoption plan (exposed, tried, activated, repeated)
- Which entry point brought the user
- Where users leave the flow, and which errors they hit
- Exposure to each experiment variant

Every event must answer at least one question. "Track everything" produces a lot of data and few answers.

## Phase 3: Write the tracking plan

| Event | Fires when (exact trigger) | Where in code | Properties | Answers |
|---|---|---|---|---|
| `Invoice Creation Started` | User opens the new-invoice form | `InvoiceForm.tsx`, once per visit | `entry_point`, `client_count` | Tried; entry-point split |
| `Invoice Sent` | Server confirms the invoice was sent | `invoices.service.ts`, after send succeeds | `amount_bucket`, `currency`, `is_first_invoice` | Value moment (activation) |
| `Invoice Send Failed` | Send rejected | same, error branch | `error_code`, `step` | Drop-offs |

Rules:

- **Follow the project's naming convention.** Without one, use `Object Action` in the past tense (`Invoice Sent`), Title Case, with the noun the product UI uses.
- **Track outcomes where they happen.** Fire value moments server-side after success when possible: reliable, unaffected by ad blockers, and not double-counted by re-renders. Track UI intent (opened, clicked) client-side.
- **Properties serve the breakdowns you'll need**: `entry_point`, plan, variant, platform. Prefer enums and buckets to free text.
- **No personal data**: no emails, names, free-text input, or anything the privacy policy doesn't cover. Use IDs.
- **Identity**: events must attach to the same user — and account, for B2B — as the product's other events.

## Phase 4: Implement

Add events through the project's wrapper, with types if the project types its events (extend the event union or schema). Put UI events in event handlers or in effects that run once per occurrence — never in render bodies, where re-renders and development double-mounts duplicate them. Put server events after the operation commits, not before.

If an experiment is running or planned, log exposure when the user actually sees the variant, not when the flag is evaluated at app start. Many flag SDKs log exposure automatically on evaluation; check before adding a duplicate.

## Phase 5: Verify

Trigger each event and confirm it fires **once**, with the right properties and identity:

- Use the SDK's debug mode, the tool's live event view, or a test that spies on the wrapper.
- Check double clicks, back navigation, and retries after errors.
- If the project tests its analytics wrapper, add assertions for the new events.

## Phase 6: Define the analysis

Write funnel and metric definitions precise enough to build in the tool: steps, conversion window, counting unit (users or accounts), and filters (eligible users only). If the analytics tool is reachable from your environment (an API, a CLI or a connected integration), offer to create the funnel and dashboard; otherwise give the exact configuration.

## Output

Write `tracking-plan.md` to the feature folder (the table, funnel definitions and verification notes), along with the code changes. Summarize: events added, how each was verified, and the questions the data still can't answer.
