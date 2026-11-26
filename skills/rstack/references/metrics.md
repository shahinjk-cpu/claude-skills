# Measuring parts, then routing by results

Routing starts from judgement: the lane grades each part as Frontier, Hard, Normal or Easy and picks the model. In one window the main conductor does this. That is a good first guess. Measurement then shows where the guess was wrong, for example a cheap model that needs four attempts costs more than a strong one that needs one.

## Record one row per part

Append to `metrics.parts_file` (default `metrics/parts.tsv`) when a part lands (or is abandoned). The sub-conductor that ran the part writes the row; the conductor fills `escaped` later if a defect from it is found after merging.

```
date	lane	part	task_type	grade	model	attempts	verdict	p1_count	cost_usd	minutes_to_merge	escaped
2026-11-23	billing	refund-retry	backend-fix	Hard	claude-opus	1	PASS	0	3.10	95	0
2026-11-23	docs	api-dashes	wording	Easy	deepseek-flash	2	none	0	0.04	40	0
```

- `task_type`: a short, stable label (backend-fix, ts-refactor, unit-tests, wording, migration, infra, ...). Keep the list small so the numbers add up.
- `attempts`: number of builder runs. First pass means the part was accepted after one run with no P1.
- `verdict`: final landing status. Use `PASS` for a part cleared after a fix, `PASS WITH FOLLOW-UPS` if it landed with follow-ups, `none` if it landed without a review, or `abandoned` for stopped work. Keep original reviewer verdicts in their own files.
- `cost_usd`: from the provider's reported usage where available; otherwise tokens, and say so.
- `escaped`: defects found after merge that trace to this part.

## Read it weekly

`scripts/route-stats.py metrics/parts.tsv` prints, per task type and model: parts, first-pass rate, average attempts, P1s per part, average cost, cost per accepted part, minutes to merge, escaped defects.

The weekly cost-and-usage audit turns that into routing changes in `conductor.config.json`:
- **Move work down** to a cheaper model when, for that task type, it has at least 5 parts, a first-pass rate of 80% or more and no escaped defects.
- **Move work up** when a model's cost per accepted part is higher than the next grade's, or it has an escaped defect on that task type.
- **Change one thing at a time**, and note it in the decision trail with the numbers behind it.

Also track the overhead: conductor tokens per landed part. If it rises, the conductor is doing work that belongs to sub-conductors or agents.
