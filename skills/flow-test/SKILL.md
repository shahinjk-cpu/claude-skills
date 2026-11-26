---
name: flow-test
description: Turn a user flow into an end-to-end test with a UX budget — the test fails when the happy path needs more clicks, fields or page loads than allowed, so UX regressions break CI the way performance regressions do. Playwright by default, adapted to Cypress or the project's existing E2E setup. Use when asked to test a flow, add a click budget, keep onboarding, signup or checkout from getting longer, or after a happy-path audit sets a budget.
---

# Flow Test

A flow that took 6 clicks at launch takes 11 a year later, one reasonable PR at a time, and nothing fails along the way. This skill makes the flow's cost an assertion: an end-to-end test walks the happy path the way a user would, counts the interactions, and fails when the count exceeds the budget.

## Phase 1: Find the E2E setup

Look for an existing end-to-end stack: `playwright.config.*`, `cypress.config.*`, `wdio.conf.*`, Maestro or Detox for mobile. Reuse its config, fixtures, authentication helpers, test-data seeding and CI job.

If there's none, propose Playwright and ask before adding it: a new tool in the project's toolchain is the team's decision.

## Phase 2: Get the flow and the budget

Read `flow-audit.md` in the feature folder (`docs/product/<feature-slug>/`) for the steps and the budget. Without one, trace the happy path quickly (entry point → steps → goal state) and set the budget to today's count: the test's first job is to stop the flow from getting worse.

What to assert, depending on the flow:

- **clicks** — activations of controls: buttons, links, options, checkboxes, tabs, including opening dropdowns and closing modals.
- **fields** — distinct inputs the user fills.
- **navigations** — page loads and client-side route changes after the start state.
- **time** (optional) — only with a generous margin, because CI machines are noisy.

These match the definitions in `happy-path-audit`, so the audit's budget can be asserted as is.

## Phase 3: Add the UX meter

Count interactions in the page, not in the test code. A listener on real DOM events counts every click, whichever helper or page object produced it. Add this once next to the project's other fixtures, adapted to its language and conventions (Playwright with TypeScript shown):

```ts
// e2e/fixtures/ux-meter.ts
import { test as base, expect, type Page } from '@playwright/test';

export type UxBudget = { clicks?: number; fields?: number; navigations?: number };

export class UxMeter {
  clicks = 0;
  fields = 0;
  navigations = 0;

  constructor(private readonly page: Page) {}

  async install() {
    await this.page.exposeBinding('__uxMeter', (_source, kind: 'click' | 'field') => {
      if (kind === 'click') this.clicks++;
      else this.fields++;
    });
    await this.page.addInitScript(() => {
      const report = (kind: string) => (window as any).__uxMeter?.(kind);
      const touched = new WeakSet<EventTarget>();
      const onField = (event: Event) => {
        if (event.target && !touched.has(event.target)) {
          touched.add(event.target);
          report('field');
        }
      };
      addEventListener('click', (event) => { if (event.isTrusted) report('click'); }, true);
      addEventListener('input', onField, true);
      addEventListener('change', onField, true);
    });
    this.page.on('framenavigated', (frame) => {
      if (frame === this.page.mainFrame()) this.navigations++;
    });
  }

  /** Call once the start state is visible (after login, seeding and the first goto). */
  start() {
    this.clicks = 0;
    this.fields = 0;
    this.navigations = 0;
  }

  expectWithin(budget: UxBudget) {
    const actual = { clicks: this.clicks, fields: this.fields, navigations: this.navigations };
    base.info().annotations.push({ type: 'ux-budget', description: JSON.stringify({ actual, budget }) });
    for (const key of Object.keys(budget) as (keyof UxBudget)[]) {
      expect(actual[key], `UX budget exceeded for ${key}: ${JSON.stringify(actual)}`)
        .toBeLessThanOrEqual(budget[key]!);
    }
  }
}

export const test = base.extend<{ ux: UxMeter }>({
  ux: async ({ page }, use) => {
    const meter = new UxMeter(page);
    await meter.install();
    await use(meter);
  },
});
export { expect };
```

What it counts:

- Playwright's `click`, `check` and `tap` produce trusted events and are counted. Clicks dispatched by the app's own JavaScript are not.
- `fill` and `selectOption` count one field per input, however many times it's edited. They don't count a click: focusing a text field is part of filling it. A native `<select>` costs a real user two clicks — add them to the budget by hand if the flow has one.
- A checkbox or radio counts as one click and one field. Set budgets from a measured run, not only from the audit's arithmetic.
- `framenavigated` fires for full page loads and for client-side route changes. If the app rewrites the URL several times per screen (query parameters, redirects), assert clicks and fields and leave navigations out.
- For Cypress or another runner, keep the same design: a page-side listener on `click`, `input` and `change` in the capture phase, reset at the start state, asserted at the goal state.

## Phase 4: Write the tests

Happy path first. Walk it like a user: role- and label-based locators (`getByRole`, `getByLabel`), which survive refactors and double as an accessibility check. Seed the start state through the API if that's faster, but never take API shortcuts for the steps being measured.

```ts
import { test, expect } from './fixtures/ux-meter';

test('first invoice is sent within budget', async ({ page, ux }) => {
  await page.goto('/dashboard'); // signed in through storageState
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  ux.start();

  await page.getByRole('button', { name: 'New invoice' }).click();
  await page.getByLabel('Client').fill('Acme');
  await page.getByRole('option', { name: 'Acme Corp' }).click();
  await page.getByLabel('Amount').fill('1200');
  await page.getByRole('button', { name: 'Send invoice' }).click();

  await expect(page.getByText('Invoice sent')).toBeVisible(); // goal state
  ux.expectWithin({ clicks: 3, fields: 2 });                  // budget from flow-audit.md
});
```

Then the critical unhappy paths listed in `unhappy-paths.md`. Simulate failures with network interception (`page.route` returning a 500 or a validation error) and assert the recovery: the error is visible, the input is kept, and the user gets back on the path within a small budget.

## Phase 5: Make the budget a team rule

- Keep budgets next to the test, or in one `ux-budgets.json` when there are several flows, so any budget change shows up in the diff.
- The failure message must say what to do: if the extra step is intentional, raise the budget in the same PR and justify it in the description; otherwise remove the step.
- Ratchet: when a PR makes the flow shorter, lower the budget in that PR.
- Run the tests in the existing CI job. The `ux-budget` annotation records the measured counts, so `ux-review` can show before and after on a PR.

## Output

The fixture, the flow tests and the budgets committed to the repo, with a run that passes — or that fails on an existing regression, which you report. Summarize: flows covered, budgets set (current and target), and any flow already over its target.
