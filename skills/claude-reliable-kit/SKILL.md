---
name: ask-smart
description: Decides whether to ask or proceed. Use when a request is vague or high-stakes ("build me an app", "make it robust") and a wrong guess would waste real work. Skip for clear tasks.
---

# Ask Smart

Ask only when the answer changes what you build. Facts are your job (read the code, config, docs, and conversation); decisions about goals, policy, and trade-offs are the user's.

## Decide

- **Cheap to redo or easy to correct:** don't ask. State the assumption in one line and proceed.
- **Expensive to redo, or several valid readings with very different results:** ask before the dependent work. Keep doing independent discovery meanwhile.
- **Destructive, irreversible, external, or spends money:** always confirm first.

## Ask in one round

- Put every question that is answerable now into one numbered message, at most 3 (one at a time only when later questions depend on earlier answers).
- Each question names the decision, offers 2-4 concrete options, and leads with your recommended default so a plain "yes" accepts it.
- Ask only about outcome-changing choices: audience, behavior, scope, constraints, acceptance criteria, important failure cases.
- Never ask what is already stated, has an obvious default, or is clearly part of the request ("Would you like me to also...?").
- If nobody can answer right now (automated or non-interactive run), do only the safe, reversible part, then list the questions with your defaults and stop before the costly part.
- Stop asking once you can predict the user's answers. If the user says "just pick" or "whatever you think", pick, say what you picked, and move on.

## Before building

Restate the goal in one or two lines with your assumptions and an explicit "Out of scope:" line. On a multi-step task, record the agreed goal and requirements (`python ${CLAUDE_SKILL_DIR}/../task-ledger/scripts/ledger.py goal "..."`, `add req "..."`) so they are proven before you finish. Treat later corrections as updates to that statement, and make assumptions easy to change in the code.
