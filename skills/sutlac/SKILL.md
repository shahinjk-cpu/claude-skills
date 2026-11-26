---
name: is-ac
description: Use when opening a new task - when the user describes a bug or request, when a finding outside the current scope comes up during work, or when another area needs a notice. Searches existing tasks first and opens no new task if one matches; otherwise writes the task file under docs/tasks/ with durable text and observable acceptance criteria. On request, adds the design as a dated comment.
argument-hint: "[short description, in your own words]"
---

# Open a task

> **Prefix and project info.** Below, `PREFIX-N` is a task number; the prefix is in `docs/config.json` > `prefix` (e.g. `KES` → `KES-12`, file `docs/tasks/KES-12.md`). In commands, write the real prefix in place of `PREFIX`. Everything project-specific (the check command, areas/apps, test accounts, the pitfalls of parallel work) is in the root `CLAUDE.md` and in `docs/knowledge/`; this skill reads it from there and does not assume it from memory.

A task is read months after it was found, by someone who wasn't there, after the code around it has changed. Write for that reader.

Format, template and queries: `docs/tasks/README.md`. Valid values are in `docs/config.json`; read them from there, don't write them from memory.

## Step 1: Don't open without searching

**No task is opened without a search.** Not for an obvious bug, not for something you just found yourself, not for a piece that falls out while splitting a task. The search gets skipped most where "this is definitely new" is said; when it is skipped, the same topic splits into two separate records.

At least two searches, with two different vocabularies; closed tasks included:

```bash
grep -li '<symptom, in product language: "order cancellation", "invoice attachment">' docs/tasks/PREFIX-*.md
grep -li '<mechanism: endpoint fragment, error code, field name>' docs/tasks/PREFIX-*.md
```

Show the title and status of the hits in one go: `grep -H -e '^title:' -e '^status:' <files>`.

- **Open match** → don't open a new task. Add the evidence to that task: if it is a notice for another area, a dated line in `## Notlar` (notes); otherwise a comment in `## Yorumlar` (comments). If it changes the scope, say so in that comment.
- **Partial match** → write there first, make only the uncovered remainder a new task, and state in the first line of its `## Bağlam` (context) which task it was split from.
- **Closed match** → this is a regression, not the same task. Open a new task and write `Regression: PREFIX-N` in the first line.

Tell the user in one sentence which searches you ran and what came up. A search that isn't reported counts as not done.

## Step 2: One task or several

Problems that can be fixed separately and verified independently of each other are separate tasks. Symptoms that come from a single root behaviour are one task. If undecided, pick the thin task: a thick task with two of its three criteria passing neither closes nor goes back.

- If more than one area (app, package) carries the same change, it is one task with all the tags: `tags: [api, web]`. A separate task per area only if the work will really be done at separate times.
- When splitting, open the blocker first and write `After: PREFIX-N` in the Bağlam of the one that follows. Use this line only for real ordering (B can't be tried before A is finished); to say "related", use `Related: PREFIX-N`.
- Each piece is a separate task and needs the Step 1 search separately.

**A second pair of eyes first on a big task.** If the task brings a new screen, table, app or sync, changes more than one area, or will take longer than a few days, have a sub-agent critique the proposal and what Step 1 found before you write it (if the project has an agent for critique or architecture under `.claude/agents/`, that one; otherwise a general sub-agent: "is this task needed, can it be made smaller, who will use it?"). Show its verdict (including "Shrink it" and "Drop it") to the user; the user decides. It is not called for a bug fix or a small task. If the solution has more than one serious option, the comparison goes into the design comment in Step 5.

## Step 3: Write

The test: after a refactor renames every file the task touches, does the task still say something true?

- **Write the behaviour, not the code.** "A branch user sees another branch's order in the order list", not "`buildOrderFilter` skips the scope". The second becomes wrong the moment the function is split, and ties the solution to one place.
- **No file path, line number or symbol name in Bağlam and Kabul.** They are what goes stale fastest. An endpoint path (`GET /api/v1/orders`) and a field name are a contract and may be written.
- **The product's own words:** the name the user and the team give that thing (order, branch, invoice...). Don't invent module names.
- **For a bug, reproduction steps are mandatory:** numbered, concrete; which role, which account, which data. If you can't reproduce it, what you have is a suspicion, not a task; write it as a comment on a related task.
- **Raw evidence** (stack trace, query output, failing test) sits in Bağlam inside a code block, with what produced it and at which commit written down. The text around it must make sense on its own even after the block goes stale.
- **Readable in thirty seconds.** Something that needs a long explanation is usually something that needs splitting.

### Kabul

`## Kabul` (acceptance criteria) is the list of what will be proven when the task is closed. Each item is a claim that can be called true or false without reading the code; numbered, one per line:

```md
## Kabul
1. A branch user sees only their own branch's orders in the order list.
2. The detail of an out-of-scope order returns 403.
```

A criterion that can't be observed ("the code will be cleaner") can't be proven at closing; either make it observable or remove it. `## Yapılacaklar` (to-dos, `- [ ] api: ...`) is how the work is split up, Kabul is what will be true.

### Fields

- `status: todo`. Don't start a task opened for someone else and don't put it in a sprint: `sprint` stays empty unless the user says otherwise.
- `priority`: `normal` unless the user said otherwise. A data leak in production, an authorization hole or a bug that stops the customer is `high`; if so, propose it.
- `title` is a sentence, not a label: "Order list doesn't apply branch scope", not "Order bug".
- `created`: `date +%F`.

Number: `bunx sutlac next` (if the command is missing, `docs/tasks/README.md` > New task). Right before writing the file, check that the number is free (`ls docs/tasks/PREFIX-<N>.md`).

## Step 4: Approval and commit

If the user didn't ask for the task themselves (a finding from ongoing work, a notice task), show the title, tags and Kabul before writing the file and get approval. Don't open a task without approval.

After opening, state the number and the file path. Opening a task doesn't require a commit; if it is part of ongoing work it goes into the same commit as that work, otherwise into a `docs: open PREFIX-N` commit (show the message, get approval).

## Step 5: Design (on request)

If the user wants to open the task by talking through the "how", the design is written **as a comment**, not in the body: the body is the durable problem definition, the design is a snapshot of one particular day and may contain file paths and symbol names. Don't write a plan, don't break it down file by file: the code changes before the task starts, and an old plan sends its reader to the wrong place.

```md
### 2026-10-25 14:10

**Design — 2026-10-25**

Behaviour and scope: ...
Decisions: ... (what each rests on)
Questions asked:
- Question: ... · Choice: ... · If not asked: ...
Rejected options: ... (why)
Criteria tests can't prove: ... (why)
```

`/is-baslat` reads this comment and checks whether it still holds against the code.

## Asking questions

The same rule in this skill and in `/is-baslat`:

- **Describe the situation before asking:** what is happening and for whom, where you found it (the result, not a search dump), what you plan to do, which questions remain open. A few sentences; a summary longer than one screen isn't doing its job.
- **Ask only if these three are true together:** two readings lead to clearly different work, the repo (rule, convention, existing code) doesn't settle it, the wrong choice is expensive. Otherwise decide and record it.
- **One question, recommended option first** (`(Recommended)`); the option description states the outcome for the product, not the mechanism.
- **The answer goes on record:** what was asked, what was chosen, what would have been done had it not been asked. Without the third, nobody can tell later whether the user changed the outcome or confirmed it.

## Rules

- No task without a search; no new task if there is a match.
- Bağlam and Kabul describe behaviour; file paths stay in Notlar and in the design comment.
- Kabul items are observable claims.
- A task opened for someone else is `todo` and has no sprint.
