---
name: experiment-readout
description: Analyze a finished A/B test and recommend a decision — validity checks first (sample ratio mismatch, duration, exposure), then lift, confidence intervals and p-values from a bundled script, guardrails and pre-registered segments, and a ship / iterate / roll back call with a stakeholder summary and flag cleanup. Use when an experiment has ended, or when someone asks "did the test win?", "is this significant?", or to read A/B results.
---

# Experiment Readout

The readout is where experimentation most often loses its value: a dashboard shows +4 % in green, someone ships, and nobody checks whether the test was valid or whether +4 % is noise. This skill checks validity before results, computes the numbers reproducibly, and states the decision together with its uncertainty.

## Phase 1: Gather the spec and the data

Read `experiment.md` in the feature folder (`docs/product/<feature-slug>/`) for the pre-registered primary metric, guardrails, MDE, duration and segments. Without a spec, reconstruct it with the user and label the readout as post hoc.

Get raw numbers per variant: users (randomization units) and conversions, or users, mean and standard deviation for continuous metrics. Sources, in order of preference: a warehouse query, the experimentation or analytics tool's API or export, numbers the user pastes. Prefer raw counts to percentages copied from a dashboard.

## Phase 2: Check validity before reading results

Stop and report if a check fails. A result from an invalid test isn't weak evidence; it's no evidence.

1. **Sample ratio mismatch (SRM).** Do the variant sizes match the planned split? The script below runs a chi-square test; p < 0.001 means assignment or exposure logging is broken (bots, redirects, a variant that crashes before logging). Find the cause; don't adjust the numbers.
2. **Duration.** Did the test run its planned duration, in whole weeks? Was it stopped early because it looked good?
3. **Sample size.** Did it reach the planned sample? If not, it's underpowered and a non-significant result says little.
4. **Stability.** Did anything change mid-test (allocation, targeting, variant code, an outage)? Data from before a change can't be pooled with data from after.
5. **Exposure.** Are only exposed, eligible users counted?

## Phase 3: Compute

Run the bundled script, in the `scripts/` folder next to this file:

```bash
# Conversions: users and conversions per variant
python3 scripts/readout.py --control 48210 5302 --treatment 48655 5598 --mde 0.05

# Continuous metric: users, mean and standard deviation per variant
python3 scripts/readout.py --control-mean 48210 41.2 38.5 --treatment-mean 48655 42.0 39.1
```

It prints the SRM check, each variant's rate or mean, the absolute and relative differences with 95 % confidence intervals, the p-value, and a verdict against the MDE. Run it for the primary metric and for each guardrail.

For metrics whose unit differs from the randomization unit (revenue per order, clicks per session), this script underestimates the variance. Use the delta method or the experimentation platform's computation instead, and say so in the readout.

## Phase 4: Interpret

Read the confidence interval, not only the p-value:

| Interval for the relative lift | Meaning |
|---|---|
| Entirely above zero and above the MDE | Clear win |
| Above zero, but includes lifts smaller than the MDE | Real, possibly too small to be worth maintaining: judgment call |
| Includes zero, stays within ± MDE | Flat: no effect large enough to matter. A useful result |
| Includes zero and reaches beyond ± MDE | Inconclusive: the test was too small to tell |
| Entirely below zero | The change hurts |

Then:

- **Guardrails** — a guardrail significantly worse beyond its threshold blocks shipping, whatever the primary metric says.
- **Segments** — only the pre-registered ones. With 20 post-hoc segments, one will look significant by chance; report post-hoc patterns as hypotheses for the next test.
- **Novelty** — with daily data, check whether the lift shrinks over time. Early lifts on visible changes often fade.
- **Practical size** — translate the lift into what it means: "+0.6 pp activation ≈ 140 more activated teams a month".

## Phase 5: Decide and clean up

Recommend one of:

- **Ship** — roll the variant out to 100 %, then remove the flag and the control code.
- **Iterate** — the direction is promising or the learning is clear; propose the next test.
- **Roll back** — keep control and remove the variant code.

Whatever the decision, create the task or PR that removes the flag. Dead flags are permanent complexity.

## Output

Add a `## Readout` section to `experiment.md` (or write `readout.md`): validity checks, a results table for the primary metric and guardrails with the commands that produced it, the interpretation, the decision, and what was learned. Open it with a five-line summary for stakeholders: decision, primary result with its interval, guardrails, confidence, next step.
