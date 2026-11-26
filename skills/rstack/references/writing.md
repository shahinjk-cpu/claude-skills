# Writing: plain prose, and PR descriptions anyone can follow

Agents write a lot: PR descriptions, commit messages, summaries, plans, verdicts, messages to the human. If a busy reader cannot tell in ten seconds what changed and whether it is safe, the writing failed, however correct it is.

## The plain-prose pass (run it on everything before it is sent)

- **Lead with what changed** for the reader, in their terms, not the implementation's.
- **Short sentences, everyday words.** Replace jargon with what it means; if a term is needed, say what it is the first time.
- **Concrete over vague**: numbers, names, dates, file paths. "Refunds now post within 2 minutes" beats "improved refund handling".
- **Cut the filler**: no "it is worth noting", no "robust", "seamless", "leverage", no restating the question, no sign-off lines.
- **No hype and no hedging**: say what is true and how sure you are. Label claims measured, inferred or guessed.
- **Plain punctuation**: one idea per sentence; avoid stacked dashes, semicolons and parentheses inside parentheses. Lists for steps and choices, prose for reasoning.
- **Check every number** against git, CI, logs or the code before it goes in.
- **Never paste private detail** into anything shared: credentials, personal data, local paths, raw chat.

## Plans and reports

- Describe what the work does and how it will be checked. Name a helper script or config key only after a read confirms it exists in the target repo and the reader needs it. Leave out internal tool names, defaults and phrases such as “as the skill requires”.
- Base time, size and cost estimates on the target repo's record or current measurements. State the basis. Leave the estimate unknown when there is no credible basis. Never reuse numbers from a worked example.
- Give the human their list of asks followed by a one-screen plan. Put work tables, timelines, evidence and other detail in appendices. Keep the whole document under about 1,500 words; when it grows past that, cut detail rather than move it around. Report process decisions after making them.
- Write each human ask with the exact command or click path and what to send back. "The script I give you" is not an ask anyone can act on.

## PR descriptions

Write for someone who has not seen the work: a reviewer, the human, the next agent. Use the same sections every time so readers know where to look.

```
## What it does
One or two plain sentences on the change a user or operator will notice. Then bullets for the main parts.

## What it fixes
The problem in plain words: what was wrong, who it affected, how it was found (link the issue or cause file).

## How it applies
How it reaches users: deploy, migration, flag (and its default), config, data steps, order of operations.
How to undo it if needed.

## Tests and checks
What was run (with counts) and what was not run and why. CI is the judge for the rest.

## Reviews
Each part and its verdict file, or "none needed (wording only)" under the review policy.

## Docs
Which docs changed, or "No doc change: <reason>".
```

For a train (several parts in one PR), add a table at the top:

| Part | What it does | Commits | Review | Notes |
|---|---|---|---|---|

Rules that keep PR descriptions useful:
- The first line of "What it does" should make sense to someone who reads nothing else.
- Say what is switched off: "lands dark behind <flag>, default off" is the most important sentence in many PRs.
- Say what loosened, if anything (a raised limit, a relaxed check), in the first lines, with the reason. Hidden loosening is how regressions ship.
- Name risks and the rollback; never leave a reader to infer them.
- Keep it current: when the PR changes after review, update the description in the same push.

## Commit messages

Subject: what changes, in the imperative or as a plain statement, under about 72 characters. Body: why, and anything a future reader would need (the cause, the decision, the numbers). No AI attribution lines.

## Messages to the human

Lead with the outcome or the decision needed. One list for their actions, each with the exact command. Decisions as one-word choices with the recommendation first. Keep detail in links.
