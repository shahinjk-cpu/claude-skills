# Templates

Give each agent the goal, exact scope, files, rules and report format. Use the named base when the part depends on an open branch.

## Builder brief

```
You are a builder for <project>. Build ONE part, then stop.

GOAL: <one sentence, the behaviour that must exist after>
SPEC: <path to the spec, or the spec inline: files, functions, the change>
BASE: create your own worktree: git worktree add <path> <base> -b <branch>
      Work only there. Never git stash/reset --hard/checkout in any other checkout.
TESTS: add <named tests>, each with its inverse (the refused case AND the case that must still pass), per references/testing.md.
       Run only your own test files, through <the shared run lock>, with <N> workers.
       Do not run the whole suite; CI does.
RULES: commit as <author>; no AI attribution lines; never loosen a check, budget or timeout to go green;
       no secrets in code, logs or commits; <project rules that apply>.
OUT OF SCOPE: <what not to touch>
REPORT: clear the push gate, push the branch, open a DRAFT PR (do not mark ready), and reply with: branch, head sha (40),
        commit count, tests run with counts, anything not run and why, open questions.
```

### Sandboxed CLI builders

- Fetch the PR head locally before launch. Name its local ref and exact SHA in the brief. The sandbox has no network.
- If the sandbox cannot write the shared Git metadata, prepare a private `GIT_DIR` with the base and use it with the builder's `GIT_WORK_TREE`. Have the builder commit there. Have it create a bundle that names the result ref and verify the bundle. Return the bundle path, ref and head SHA with the test report.
- Fetch the verified bundle into a temporary ref in the conductor's checkout. Check the fetched SHA against the report. Check that the builder's worktree equals the bundle head's tree, including file modes and any untracked additions. Move the intended branch to that head only after the checks pass. Stop if the branch moved since handoff.

## Reviewer brief (when the review policy calls for one)

```
You are an independent reviewer of <PR/branch> at head <sha>. You did not build it. Read only:
no commits, pushes, comments or edits. (Use git show/diff on refs; tests only in your own throwaway worktree.)
MODE: <combined, spec or outcome>
CONTEXT: <for combined or spec, the spec and the candidate change>
         <for outcome, only the original goal, the repository and the candidate change>
CHECK, citing file:line:
  1. <the behaviour and its inverse, or the real path and what it misses in outcome mode>
  2. <the security or money property that must hold>
  3. <the seam most likely to be wired wrong: a default, a paginator, an aggregation dropping an input>
  4. run <the affected test files>
WRITE <verdict path>:
  line 1 exactly: VERDICT: PASS | VERDICT: PASS WITH FOLLOW-UPS | VERDICT: FIX
  line 2: Reviewer: <who>, <UTC time>
  line 3: Head: <sha>
  then findings ranked P1 (must fix before landing) / P2 / P3, each with file:line and the fix.
Final message: line 1 of the verdict and a five-line summary.
```

Use one brief per part. For high-impact work, give a stronger independent reviewer a combined brief with the risky failure cases. For a standalone outcome review, omit the plan, spec and builder's reasoning. Send a critical fix back once to the reviewer who found it. Name only the fix and the affected check to run.

## Cause reader brief (before any rerun or fix)

```
You are an independent cause reader. Read only. QUESTION: run <id> failed on <test>.
Decide ONE: (A) caused by the diff, (B) nondeterministic test or runner, (C) defect already on main.
Evidence: whether the relevant tree differs between the failing head and a passing one; the failing
assertion and its values; history of this test in recent runs; the runner.
WRITE <cause path>: line 1 "CAUSE: A|B|C ...", line 2 reader and time, then evidence with run ids and
file:line, whether a rerun is justified, and the fix at the cause with its owner.
```

## Investigation brief (production bug, read only)

```
Read-only investigation of <symptom the user saw>. Use <read-only identity> only; if a read is denied,
STOP and report the gap; never use another identity. No writes, no task launches, no requests as the user.
Find: the code path (file:line), the data dates involved, when it started (logs), the blast radius
(one user or all), and the class (every sibling with the same shape). Cause BEFORE any fix.
```

## Conductor messages to lanes

- One message per decision batch, not per thought. Name the PR, the head sha, the ruling and the next action.
- Quote the human's exact words when relaying a decision.
- Give the exact next action. For example, `Rebase onto <sha>, push once and wait for deciding CI`.
- Rulings that will be needed again (lock order, landing order, a product rule) go into a rulings file and the ledger.

## Production write card

```
CARD: <what changes>, <why>
Identity: <role>; Preconditions: <reads that must be true first>
Dry run: <command>; expected: <exact counts>
Apply: <command>; refuses unless the dry run's counts match
After read: <command>; expected: <counts>
Undo: <exact command>, and when to use it
Report after: <who is told, what line>
```

## Engineering checks to include when they apply

- For charges, sends, creates and deploys, make duplicate requests safe with keys or unique constraints. Test the second run.
- When replacing a path, migrate all callers and remove the old path in the same change. This keeps one source of truth.
- Verify every reported number and exercise the real user path before claiming a fix.
- Use types, enums, constraints or state transitions to prevent invalid combinations.
- For a restore or rollback, fail a release in a test, restore it and verify the previous version and data.

Use least-privilege identities. Stop and report a denied permission. Send privileged steps to the human in one ready script that stops on unexpected counts and asks for typed confirmation. A request to run until done lifts only pauses the human explicitly names.
