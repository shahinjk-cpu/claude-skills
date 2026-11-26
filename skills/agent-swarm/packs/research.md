---
name: research
description: Research team: multi-angle web and document research, synthesis, fact-checking and a sourced report.
triggers: [research, compare, survey, literature, study, report, investigate, options, alternatives]
extends: general
---

## Roles

### source-hunter
- type: researcher
- model: cheap
- rules:
  - One angle per agent (official docs, news, academic, community, data). List sources, each with its date and a one-line summary.

### deep-reader
- type: researcher
- model: standard
- verifier: fact-checker
- rules:
  - Read the assigned sources in full. Extract claims, each with its exact source and date.

### synthesizer
- type: writer
- model: strong
- verifier: fact-checker
- rules:
  - Answer first, then the evidence, then disagreements and gaps. Every claim cites its source.

### fact-checker
- type: verifier
- model: standard
- rules:
  - Read-only. Re-open each cited source and confirm the claim; flag anything stale, misread or unsupported.

## Pairings
- Broad questions: several source-hunters (one per angle), then deep-readers, then synthesizer, checked by fact-checker.

## Guardrails
- Public sources only; never sign in, download or fill forms. Quotes under 15 words.
