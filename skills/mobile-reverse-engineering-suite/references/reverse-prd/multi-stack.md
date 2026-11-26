# Multi-stack & multi-source-of-truth systems

Read this when the system has several stacks, several services sharing data, or several places that can hold the same business fact.

## What to map

- **Bridges**: shared tables, shared sessions/cookies, shared cache keys, queues, webhooks, HTTP calls between stacks, cron-driven sync scripts.
- **Ownership**: for each shared entity, which system creates it, which one updates it, which one is read by users.
- **Dual sources of truth**: name every fact stored in two places (e.g. order status in both stacks). State which wins and how divergence is detected.

## Extra checks

- **Invariant I4 is P0** for every bridge: durable divergence without reconciliation is a top risk.
- **Partial failure across stacks**: entity created in stack A, the matching process in stack B fails (and the reverse). Is there a retry, a compensating action, a reconciliation job, a manual procedure — or nothing?
- **Clock and ordering**: events from both stacks can arrive out of order; check whether status updates can go backwards.
- **Auth across stacks**: how identity and roles are propagated; can one stack trust a claim the other did not verify?

## Stack-specific hints

- **PrestaShop (1.x, legacy) + Laravel hybrid**: look for direct SQL on `ps_*` tables from Laravel, hooks/overrides in PrestaShop modules calling Laravel, shared MySQL schemas, order states stored as history rows rather than a current-state column, and admin configuration values (`Configuration` table) that switch behavior.
- **NestJS / modular backends**: inter-module calls, `EventEmitter` and message-broker handlers, queue processors (retry/backoff options, DLQ configuration), transactions spanning several repositories, and cross-module data consistency.
- **Event-sourced components**: projections vs event streams as source of truth, subscription checkpoints, replay behavior and idempotency of handlers.

## Dossier additions

- Section 1: explicit bridge map (diagram) between stacks.
- Section 6: reconciliation inventory per bridge.
- Section 7: cross-system consistency risks and missing reconciliation.
