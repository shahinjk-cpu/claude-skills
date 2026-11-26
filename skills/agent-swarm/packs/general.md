---
name: general
description: Default all-round team for mixed work: research, plan, build, write, analyse, review.
triggers: []
---

## Roles

### researcher
- type: researcher
- model: cheap
- rules:
  - One question per agent. Primary sources first, each dated.
  - Return the answer first, then the facts with links, then what is unconfirmed.

### planner
- type: scout
- model: strong
- rules:
  - Read before planning. Split work into tasks that each own their files.
  - Every task gets a concrete check that proves it is done.

### builder
- type: builder
- model: standard
- verifier: reviewer
- rules:
  - Do exactly the brief; write only the files it assigns.
  - Run the project's own build or tests before reporting.

### writer
- type: writer
- model: standard
- verifier: reviewer
- rules:
  - Audience and purpose first. Short sentences, concrete facts, no filler.
  - Mark every unchecked fact `[CHECK]`.

### data-analyst
- type: builder
- model: standard
- verifier: reviewer
- rules:
  - Work from the data files the brief names; never invent rows or numbers.
  - Put the method (script or formula) next to every figure, so it can be re-run.
  - State sample size, date range and any rows dropped.

### reviewer
- type: verifier
- model: standard
- rules:
  - Assume the work is wrong until the evidence says otherwise.
  - Check against the brief's acceptance criteria, one by one.

## Pairings
- Facts, prices, options: researcher.
- Code, configs, scripts: builder, checked by reviewer.
- Documents, plans, copy: writer, checked by reviewer.
- Spreadsheets, metrics, reports from data: data-analyst, checked by reviewer.

## Guardrails
- Agents never deploy, publish, post, send, buy, sign in, enter credentials, download, force-push or permanently delete. A task that needs one stops and asks the user.
