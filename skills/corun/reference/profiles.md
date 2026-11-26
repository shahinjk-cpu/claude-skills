# Task profiles

Every profile follows the shared process in SKILL.md (brief, independent views, produce, review, approve, learn). The profiles differ in who does what, how many reviewers read the result, and what counts as passing.

## Coding, including skill development

| Step | Who | What |
|---|---|---|
| Plan | Claude and `planner` in parallel | Architecture, data, interfaces, risks. Planner gets the brief only. |
| Build | Claude | Integration, UI, glue code, anything that needs back-and-forth with the rest of the code, and every change under a few dozen lines. |
| Build | `worker` | Self-contained modules with a fixed interface, returned as a complete file or unified diff. |
| Verify | Claude, test runs delegated to a cheaper subagent | Apply with `git apply --check`, run tests and type checks. |
| Review | two `reviewer`s | The final diff, two-tier findings, at most two rounds. |
| Wording | `planner` | User-facing text, messages, SKILL.md descriptions. Claude checks each edit against how the feature actually works. |

Passing: tests and mechanical checks green; no confirmed blocking finding. For a skill, the description triggers on the intended phrases and the scripts run from a clean checkout.

## Research

| Step | Who | What |
|---|---|---|
| Decompose | Claude | Split the question into narrow sub-questions with fixed output formats. |
| Gather | `runner` (several calls in parallel) | One sub-question per call; each claim with a source URL. |
| Synthesize | `planner` and Claude independently | Planner gets the question and the gathered material, not Claude's synthesis. |
| Verify | Claude | Open the primary source for every claim that the conclusion rests on. Mark each figure: confirmed on the primary page, confirmed only on an aggregator, or unverified. |
| Review | `checker` | Logic and consistency of the final write-up against the cited sources. |

Passing: every load-bearing claim traces to a source the user can open, with its verification level stated.

## Document writing (proposals, papers, reports, emails)

| Step | Who | What |
|---|---|---|
| Outline | Claude; `planner` critiques structure and angle | |
| Draft | Claude | Grounded in the user's own files. |
| Facts | `runner` | Bounded lookups only (a date, a figure, a citation). |
| Edit | `planner` | Prose clarity and flow. Claude accepts edits that keep meaning and tone. |
| Check | `checker` | Facts, numbers, internal consistency. |
| Outside read | `reviewer` (one call) | Read as the target audience, for example a grant panel reviewer; list the three weakest points. |

Passing: every claim rests on the user's files or a verified source; the user approves the final text.
