# Rules for test cases

Every builder follows these rules, and every reviewer checks them. Agents write tests fast, so a suite grows by duplicates and slow, flaky checks unless the rules are explicit. When the repository has its own test rules (a `CLAUDE.md`, `AGENTS.md` or test guide), read them first. They win where they are stricter.

## What to test

1. **One test plus its inverse per behaviour.** A refusal test has an allowed twin. A test that a value passes has one that a wrong value fails. Two tests that prove the same thing are one too many.
2. **Extend before you add.** Put a new case in the file that already tests that behaviour. Add a new file only for a new behaviour. Never copy a test and change one value. Use a parameter list instead.
3. **Test behaviour, not implementation.** Assert what a caller or user sees: the response, the row, the event, the charge. A test that pins a private function's call order breaks on every refactor and proves nothing about the product.
4. **Red first.** A test for a fix fails on the code before the fix and passes after it. Run it both ways and say so in the PR. A test that passes on the broken code is not evidence.
5. **Prove the real path.** "Fixed" means the user's real entry point now works, checked through it. A passing unit test next to a broken route is not a fix.
6. **Pin the class, not the instance.** When a bug is a whole class (a wrong default, a dropped input, a check missing at a boundary), add one test that scans for every instance of the class. Fix every sibling in the same change.
7. **Test the second run.** For anything that charges, sends, creates or deploys, run it twice and assert the second run changes nothing.
8. **A runtime property needs a runtime test.** A timeout, budget, lock or concurrency limit is proven by running it, not by reading the code that sets it.

## How to write it

9. **No bounds on the runner's clock.** Never assert that a real duration is small. Count work (calls, rows, bytes) instead, or use a frozen or virtual clock, or wait for an event. Code under test that has its own time budget runs on a controlled clock.
10. **Bounded waits, no sleeps.** Wait for another task, thread or database session by polling for the condition or awaiting an event, with one shared timeout constant. A fixed sleep before an assertion is a flake waiting to happen.
11. **No date that expires.** Never compare today's date with a deadline in a test. The day it passes, every PR fails.
12. **No real network or cloud.** Use fakes, stubs or a loopback server. Never catch the error a network guard raises.
13. **Shared helpers live in one support package.** Never import a helper from another test module. Move it to the support package in the same change, and reuse what is already there before writing a new one.
14. **Real services only where a fake cannot prove it.** Use the real database for locks, concurrency and its own constraints. Run those tests on CI's own harness and image, never with a tool CI does not have (a local server binary, a container runtime). Mark them so they run in the serial step.
15. **No literal revision or count that moves.** Assert a migration's place with the repository's chain helper, not a hard-coded head or "the only file with this number". A pattern that matches a revision must not also match the next migration's reference to it.

## Generated fixtures and censuses

16. **A census failure is a review.** When a generated fixture no longer matches the code, find out why first. If the change was unintended, fix the code. If it was intended, regenerate with the census's own command and review every changed row.
17. **Never hand-edit or hand-merge generated files.** After a rebase, take the base's copy and regenerate once on the final tree. Put regenerated rows in their own commit.
18. **New censuses follow one shape.** Key rows by path or symbol, not line numbers or hashes. Make the list shrink-only. Give it a `--check` mode, plus a test that fails on a planted site.

## CI wiring

19. **Files read from outside the test tree belong in CI's filters.** A test that reads a workflow, a Terraform file or a doc must be selected when that file changes. Add the path to the CI path filters in the same change, or the test never runs when it should.
20. **Moves carry every path-keyed input.** Moving or renaming a test also moves its rows in timing registries, census keys, allowlists and doc citations, in the same change.

## When a test fails

21. **Never weaken a test to make it pass.** Raising a timeout, loosening an assertion, adding a skip or deleting the case silences the instrument. Fix the cause, or fix the test only after showing it was wrong.
22. **A flaky test is a bug.** Write down its cause before any rerun, and fix the cause. Treat a flake in money, permissions or data code as a possible real bug until proven otherwise.
23. **Read the whole red run.** Fix every failure in one push. A test that also fails on the base branch is recorded as pre-existing and fixed separately, not hidden.

## What reviewers check

For every changed test, the reviewer confirms these points:
- it would have failed before the change;
- it has its inverse;
- it is not a near-duplicate of an existing test;
- it asserts behaviour;
- it uses no real clock, sleep, network or expiring date;
- any file it reads is in the CI filters.

A test that fails any of these is a finding, not a style note.
