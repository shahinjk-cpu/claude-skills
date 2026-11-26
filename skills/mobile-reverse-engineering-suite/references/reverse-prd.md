---
name: reverse-prd
description: Reverse-engineers an existing, legacy or multi-stack application (e.g. PrestaShop + Laravel hybrid, NestJS services, several services sharing data) into an audited Reverse-PRD — cross-evidenced business rules, Mermaid state machines and sequence diagrams, invariant and failure-mode audit of money flows, Gherkin scenarios. Use when asked for a reverse PRD, a functional audit of payment / payout / commission / refund flows, or product documentation of an undocumented system.
argument-hint: "[repo path(s)] [P0 domains...] [lang=<language>]"
disable-model-invocation: true
---

# Reverse-PRD

Produce a traceable Reverse-PRD of an existing system: what it really does, proven by code and by observation, focused on the risks that cost money or corrupt data. The dossier is used to make product and engineering decisions, so a visible gap is always better than a plausible guess.

## Inputs

Parse `$ARGUMENTS`:
- **Repo path(s)**: default to the current working directory. Several paths = multi-service system.
- **Domains**: optional list of P0 domains. If absent, propose them in Phase 0.
- **`lang=`**: language of the deliverable. Default English. Templates stay in English; translate headings when writing in another language.

## Non-negotiables

1. **Never invent evidence.** A value, ID, status or message not actually read or observed is written as `[Gray area / To validate]`. Fabricated precision is the worst failure of this skill.
2. **Read-only by default.** Do not modify the audited code, data or configuration.
3. **No production.** Integration observations happen only on test, staging or local environments. Any action with side effects (payment, payout, refund, email, webhook replay, order creation) needs explicit user approval first, and only on a non-production environment.
4. **No sensitive data in the dossier.** Mask PII (emails, names, addresses, phone, IBAN, card data) and never write secrets, tokens or credentials. For configuration, record variable/flag *names* and their effect, never secret values.
5. **Write to files, not to the chat.** The dossier is long; files survive context compaction. The chat only carries status, paths and questions.

## Tooling

Use what the session provides, in this order:

1. **Code-graph / semantic index tools**, if any are available (symbol search, callers/callees, impact analysis, natural-language context queries). Check the tool list; read their usage notes; pass any required project-root parameter; check index freshness when the tool exposes it and say so if it is stale.
2. **Text search** with whatever search tool the environment offers.
3. **Surgical reads**: line ranges of 10–40 lines around the symbol. Read a whole file only when it is short or central.
4. **Integration observation**: see `references/integration.md`.

- **5-File Rule**: Limit active reading to a maximum of 5 source files per P0 domain. If deeper investigation is required, rely on semantic mapping tools or search indexes. When the budget is spent, stop and mark the domain `PARTIAL`.

**Tool-call budget**: about 30 tool calls per domain, on top of the 5-File Rule. When either budget is spent, close the domain as `PARTIAL` with what is proven so far instead of continuing. The budget replaces a time limit (elapsed time is not observable) and keeps context usable for the next domains.

## Workflow

### Step 1 — Scoping (light)
Identify stacks, entry points, data stores, queues and external APIs, using only cheap queries (manifests, routing, schema files, graph overview). If the system has several sources of truth or several stacks sharing data, read `references/multi-stack.md` now.

### Step 2 — Phase 0 plan → STOP
Fill `templates/phase0.md`, write it to `docs/reverse-prd/<system>/phase0.md` in the (first) audited repo, show it to the user and **stop until they validate or amend it**. No deep exploration before validation.

### Step 3 — Prepare the dossier
Create `docs/reverse-prd/<system>/` with:
- `README.md` — the consolidated dossier, from `templates/dossier.md`; sections stay `_pending_` until Step 6.
- `domains/<nn>-<slug>.md` — one file per validated domain, from `templates/domain.md`.

`<system>` is a short kebab-case name of the audited system. Tell the user the path.

Read `references/evidence.md` and `references/invariants-failure-modes.md` before the first domain.

### Step 4 — Domains
**Subagent mode** (default when a subagent tool is available and there are 2+ domains): dispatch one subagent per domain, in parallel, with the brief in `templates/subagent-brief.md` filled in (`{{skill_dir}}` = `${CLAUDE_SKILL_DIR}`, the absolute directory of this skill; name the code-graph tools you found in Tooling so the subagent uses them too). Each subagent writes its own domain file and returns only its exit contract. Subagents do **code analysis only**: they list the integration checks to run instead of running them, because parallel browser/API sessions on shared test accounts interfere with each other.

**Inline mode** (no subagent tool, or a single domain): process domains one by one with the same template and the same exit contract.

Every domain ends with the **exit contract** at the bottom of `templates/domain.md`. Do not start consolidation with a domain lacking it.

### Step 5 — Integration pass (sequential)
Collect the integration checks from all exit contracts, deduplicate them, and run them one at a time following `references/integration.md`. If no environment is reachable, ask the user once for observations or access; otherwise leave the rules at `[Inferred from code (untested)]`. Update each domain file: confidence levels, observed values, `[CODE / UI CONFLICT DETECTED]` tags.

### Step 6 — Consolidate
Fill `README.md` from the domain files: executive summary and risk matrix, boundaries, actors, the merged business-rules table, automations, technical debt. Check every Mermaid block against the rules in `references/evidence.md`.

Final chat message: dossier path, 5-line summary of the major risks, and the open questions that block a domain.
