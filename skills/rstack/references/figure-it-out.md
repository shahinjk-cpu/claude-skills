# Figure it out

Use this when no playbook fits a large migration, an ambitious change across several areas or unclear work the human will review after stepping away. As conductor, design the workflow before anyone writes code.

## A. Frame

State what must be true on the real product to call the work done. Name the check and the result that would show the goal was missed.

Count the systems, files or records in scope. Estimate the number of units and the effort. Name each blocker and what it holds up.

State the strongest reason the request might solve the wrong problem. Test that premise with a quick read or measurement.

Set the rigor level by choosing the gates and the artifacts each gate requires. Favour stricter gates when a decision is hard to reverse or the change has a wide blast radius.

If the human is unavailable today, present the framing once and run everything reversible within scope. Follow [trust and access](trust.md#human-steps-and-queue-decisions) for steps that need the human.

## B. Design

Split the work into small units that each land on their own. Give each unit a check and a way to undo it. Resolve the riskiest unknown first.

Run lanes in parallel where the work has a clear seam. Give each lane ownership of its files and sequence edits to shared files. Follow [coordination](coordination.md#own-the-files). Choose each model by [difficulty](techniques.md#choose-the-model-by-difficulty).

Write the phase list, owners, dependencies and gates into the [plan](plan.md). Start builders and reviewers on drafts while the plan is under review.

Build the verification harness first. Run it on the current product and save the baseline before changing the product.

## C. Run the loop

Treat each unit as an experiment. State the hypothesis and make the smallest change that tests it. Inspect the actual artifact and measure the result against the baseline and the unit's check. Keep a change that clears its check. Revert a change that fails.

Give each unit the review its risk calls for. Have the reviewer inspect the artifact and run the check firsthand. See [reviews](reviews.md).

Record `VERIFIED`, `NOT VERIFIED` or `INCONCLUSIVE` for the check. Require `VERIFIED` before landing the unit or relying on its result. Draft dependent parts against a stated contract where possible. If the gate is wrong, fix it in its own change and rerun it.

## D. Keep the decision trail

As each unit lands, record the decision, reason, evidence, owner and result in the ledger and project records. Follow the [decision trail technique](techniques.md#decision-trail-in-the-records-and-locally).

## E. Verify and hand back

Run the checks from Frame on the assembled product through its real entry points. Report which checks passed, what remains open and where to find the decision trail.

Turn each recurring correction into a check, gate, lint rule or script. Use [reflect](techniques.md#reflect-turn-each-lesson-into-something-that-enforces-it).
