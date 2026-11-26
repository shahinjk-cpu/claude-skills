---
name: ab-test-design
description: Design an A/B test that can answer its question — hypothesis, one primary metric, guardrails, randomization unit, minimum detectable effect, sample size and duration with a bundled calculator — decide whether a test is worth running at all, and implement the variant behind the project's feature-flag tool (GrowthBook, LaunchDarkly, Statsig, PostHog, Optimizely, Unleash or in-house flags). Use when asked to A/B test, experiment, split test, or validate a change with data before rolling it out.
---

# A/B Test Design

An A/B test is a measuring instrument. Designed badly, it gives a confident answer to the wrong question, or no answer after six weeks of traffic. This skill writes the experiment spec before any code, checks that the test is feasible, and implements it so the data can be trusted.

## Phase 1: Write the hypothesis

> Because <evidence>, we believe that <change> for <eligible users> will <increase or decrease> <primary metric> by at least <MDE>.

Evidence comes from `brief.md`, `flow-audit.md` or `adoption-plan.md` in the feature folder (`docs/product/<feature-slug>/`), from research, or from data. Test one idea per experiment: if the variant changes copy, layout and pricing at once, a win can't tell you which change worked. Bundling is fine when you only need the decision and not the learning — say so explicitly.

## Phase 2: Decide whether to test at all

An experiment fits when the change is reversible, the outcome is genuinely uncertain, and there's enough traffic. Don't run one when:

- **It's a fix.** Ship bug fixes, accessibility fixes and repaired flows directly.
- **Traffic is too low.** If Phase 4 asks for more than about 6–8 weeks, the test won't conclude. Alternatives: test a bigger change (larger MDE), choose a more sensitive metric closer to the change, widen the eligible population, or ship behind a flag and compare before and after with qualitative feedback — while saying clearly that this is weaker evidence.
- **The decision is already made.** A test nobody will act on is waste.

## Phase 3: Choose metrics and the unit

- **Primary metric** — exactly one, chosen now. It must move if the hypothesis is true, be measurable per randomization unit, and matter to the business: the value moment beats clicks on the button you changed.
- **Guardrails** — 2 to 4 metrics that must not get worse: error rate, latency, support contacts, revenue, unsubscribes, a later step of the funnel.
- **Secondary metrics** — for learning only, never to declare a winner.
- **Randomization unit** — the user for signed-in products (stable across devices); the **account or organization** when users collaborate, otherwise teammates see different versions and contaminate each other; an anonymous ID for signed-out flows (accept some cross-device noise).
- **Eligibility and exposure** — only users who can reach the change are enrolled, and they're counted from the moment they actually see it. Users who never reach the changed screen dilute the effect.

## Phase 4: Size it

Run the bundled calculator, in the `scripts/` folder next to this file:

```bash
# Conversion metric: 12% baseline, detect a +10% relative lift, 3,000 eligible users a day
python3 scripts/sample_size.py --baseline 0.12 --mde 0.10 --daily-users 3000

# Continuous metric: standard deviation 40, detect +3 units
python3 scripts/sample_size.py --std 40 --mde-abs 3 --daily-users 3000
```

It prints users per variant, the total, and the duration rounded up to whole weeks, because weekdays and weekends behave differently and a test should never stop mid-week. Defaults: α = 0.05 two-sided, 80 % power. With more than two variants it applies a Bonferroni correction; each extra variant costs traffic, so prefer two.

Sanity check by hand for conversions: n per variant ≈ 16 · p(1 − p) / δ², where δ is the absolute difference.

The MDE is a business decision, not a statistical one: the smallest lift worth shipping and maintaining. If the answer is "any lift", no test will ever be big enough.

## Phase 5: Implement

1. **Use the project's flag tool** (GrowthBook, LaunchDarkly, Statsig, PostHog, Optimizely, Unleash, Flagsmith, ConfigCat, Vercel Flags or an in-house system) and its experiment features — assignment and exposure logging — rather than random numbers in app code.
2. **Assign deterministically** by the randomization unit, so a user sees the same variant on every visit and device.
3. **Fall back to control** when the flag service fails or times out.
4. **No flicker.** Evaluate flags on the server or bootstrap them before first render. Showing control and then switching to the variant biases the result and degrades the experience.
5. **Log exposure** when the variant renders for an eligible user. Many SDKs log on evaluation, so evaluate at the point of exposure, not at app start.
6. **QA both variants** by forcing each one through the tool's overrides, and check that tracking fires in both (`instrument-feature`).
7. **Keep the variant easy to delete**: one flag check at a boundary, not conditions scattered through the code.

## Phase 6: Pre-register the analysis

Write these down now, before any data arrives:

- The fixed duration and sample size, and the commitment not to stop early because results look good. Peeking pushes the false-positive rate far above 5 %. If the tool supports sequential testing, use its rules instead and say so.
- The decision rule: ship if the primary metric improves significantly and no guardrail degrades beyond its threshold; otherwise keep control or iterate.
- The segments you'll look at — two or three at most, chosen in advance. Patterns found in other segments are hypotheses for the next test.

## Output

Write `experiment.md` to the feature folder: hypothesis, metrics, unit, eligibility, sample size and duration (with the calculator command), implementation notes (flag key, variants, exposure point), and the pre-registered analysis plan. Summarize: duration, MDE, and anything that makes the test risky. When the test ends, `experiment-readout` analyzes it.
