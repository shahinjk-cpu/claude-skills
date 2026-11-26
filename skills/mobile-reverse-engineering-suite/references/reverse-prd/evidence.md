# Evidence rules

## Evidence format

Each business rule, state transition or invariant verdict carries evidence:

- **Code evidence**: `[Code: <file>:<line> <Class::method>]` followed by a 5–15 line extract in a fenced block.
- **Integration evidence**: `[Integration: <URL or API endpoint> · <role/account type> · <business ID> · <exact observed values>]`.

Both are expected for P0 rules. When only one exists, the confidence level says so — never fill the missing half with plausible content.

## Confidence levels

| Tag | Meaning |
|---|---|
| `[Verified UI/Code]` | Code read **and** behavior observed on an environment, consistent. |
| `[Inferred from code (untested)]` | Code read, no observation. Default for code-only subagent output. |
| `[Gray area / To validate]` | Neither proven by code nor observed (dynamic config, external service, unreachable code path). Add exactly one precise question. |

## Code / integration conflict

When code and observation disagree (different formula, feature disabled by a DB flag, dead branch actually active):

1. Do not pick one silently.
2. Document both, tagged `[CODE / UI CONFLICT DETECTED]`.
3. Describe product behavior from the observation; record the code as technical debt (dossier section 7) with the likely cause (flag, config, override, deployment drift).

## Exact values

Record real identifiers: status codes and their numeric/string values, constants, thresholds, rounding modes, currencies, delays, cron schedules, error messages verbatim. Mask PII and secrets (see SKILL.md non-negotiables).

## Source of truth

For every critical rule — always for money — state where the value comes from: table/column, runtime calculation (method), external API, environment variable or flag name, admin configuration. If two places can hold the value, say which one wins and whether they can diverge.

## Dual formulation

Every critical rule has:
- **Technical**: formula or condition as implemented.
- **Business**: one sentence a product manager can validate without reading code.

## Open questions

One precise, answerable question per gray area (who can answer it, what value is expected). Mark the ones that block a domain.

## Mermaid rules

Broken diagrams are frequent; check before writing:
- `stateDiagram-v2` for states, `sequenceDiagram` for flows.
- State ids: ASCII letters, digits, underscores. Put human labels in `state "Label with spaces" as ID` declarations.
- Avoid `()`, `:`, `;`, `#`, `{}` and accents inside transition and message labels; prefer short labels and move detail to the text.
- Use `participant X as Label` for long participant names.
- One diagram per fenced ```mermaid block, nothing else inside.
