---
name: usability-test-plan
description: Plan and synthesize a small usability test — research questions tied to a decision, participant criteria, realistic task scenarios with success criteria, a moderator script with post-task questions, a note-taking grid, and a synthesis that ranks issues by severity and frequency and links each to a fix. Works on a prototype, staging or production, moderated or unmoderated. Use when the team is unsure about a flow before building or shipping it, when analytics show a drop nobody can explain, or when asked to plan user testing.
---

# Usability Test Plan

Analytics tell you where users drop; watching five of them tells you why. A small usability test is the cheapest way to find the problems that make a flow fail — if the tasks are realistic and the moderator doesn't help. This skill prepares the test so it produces evidence, then turns the session notes into ranked fixes.

You prepare and synthesize; the team runs the sessions. Work from the notes, transcripts or recordings' transcripts the user gives you access to.

## Phase 1: Define what to learn

Write 2 to 4 research questions, each tied to a decision: "Can a first-time admin send an invoice without help?" decides whether onboarding is needed. Sources: `flow-audit.md`, `unhappy-paths.md` and `adoption-plan.md` in the feature folder (`docs/product/<feature-slug>/`), funnel drop-offs, support tickets.

Choose what to test, as early as the question allows: a clickable prototype, a staging build, or production. Testing before the code exists is the cheapest moment to be wrong.

## Phase 2: Participants

- **How many** — five per distinct user segment is the usual starting point for finding the main problems in a flow. It's not enough to measure success rates precisely; don't present percentages from five people as statistics.
- **Criteria** — the segment, experience with the product (first-time or returning), the device. Exclude employees, UX professionals and recent participants.
- **Recruiting** — existing users through the product or customer success, or a panel service; an incentive; consent to record.

## Phase 3: Write the tasks

Write scenarios that give a goal and a context, never instructions:

- ✅ "Your client Acme just confirmed the job. Bill them €1,200 for it."
- ❌ "Click New invoice and fill in the form." — this tests reading, not the product.

Don't use the interface's own labels in the task; it turns the test into a word-matching game. For each task, define:

| Task | Start state | Success criterion (observable) | Time limit | Counts as assisted when |
|---|---|---|---|---|

Order: an easy warm-up first, then the most important tasks while participants are fresh. Four to six tasks fit a 45-minute session. Include an unhappy path when it matters (an expired card, an empty list), set up in the test data beforehand.

## Phase 4: Moderator script

1. **Introduction** — "We're testing the product, not you. Please think out loud. There are no wrong answers, and you can stop at any time." Confirm consent to record.
2. **Warm-up** — two or three questions about their context and how they handle this job today.
3. **Tasks** — read each scenario, then stay quiet. Neutral prompts only: "What are you looking for?", "What do you expect to happen?", "What are you thinking?" Don't help; if the participant is stuck past the time limit, help once and mark the task as assisted.
4. **After each task** — the Single Ease Question: "Overall, how easy or difficult was this task?" on a scale from 1 (very difficult) to 7 (very easy), then "Why that score?"
5. **Wrap-up** — "If you could change one thing, what would it be?" and anything they want to add.

For an **unmoderated** test, every task must stand on its own: add an explicit "I'm done" and "I give up" option, and ask the post-task questions in writing.

## Phase 5: Note-taking grid

One row per participant and task:

| Participant | Task | Outcome (unaided / assisted / failed) | Time | Ease (1–7) | Detours and errors | Quotes | Issue observed |
|---|---|---|---|---|---|---|---|

Write down what people **did**, separately from what they **said**. When the two disagree — "that was easy", after three wrong turns — behavior wins.

## Phase 6: Synthesize

1. **Task results** — per task: unaided, assisted and failed counts, median time, median ease score.
2. **Issues** — for each problem: what happened, where (screen and component, with the file when you can find it), how many participants hit it (3 of 5), and its severity:
   - **Blocker** — prevents completing the task.
   - **Major** — causes a long delay, an error, or visible frustration.
   - **Minor** — noticed and recovered from quickly.
3. **Rank** issues by severity, then by frequency. One participant hitting a blocker is enough to fix it.
4. **Link each issue to a fix and an owner**: copy, layout, flow (`happy-path-audit`), error handling (`unhappy-paths`), or a hypothesis worth testing at scale (`ab-test-design`).
5. **Note what worked**, so the next redesign doesn't break it.

## Output

Write `usability-test.md` to the feature folder: research questions, participant criteria, tasks, script and grid before the sessions; after them, task results, ranked issues with fixes, and what worked. Summarize: whether the research questions are answered, the top three issues, and the decision they support.
