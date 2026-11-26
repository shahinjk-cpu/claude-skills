# Reviewing a part or a plan

Give each part one review. Pick it by risk and keep the repo's required approvals in force.

| Scope | Default review |
|---|---|
| Docs, wording, comments, generated files, fixture text or test-only coverage with fully specified behaviour | The launching window reads the diff. Tests and CI decide. |
| Normal code | One reviewer who did not build the part checks spec and outcome together. |
| High-impact code | One stronger independent review checks the spec, real path and risky failure cases. This includes money, billing, auth, tokens, permissions, security, migrations, production data and irreversible code paths. |
| Each large-scale work item | Check the assembled outcome once. Reuse a part's review if it covers the whole item. |
| Large-scale plans, designs and threat models | Two or three independent model families review in parallel. The conductor combines findings once. |

Use a reviewer who did not build the part. Prefer a different model family, especially for high-impact work. If none is available, the conductor picks a fresh reviewer from an available family and reports the ruling afterward. A separate item outcome covers the assembled behaviour.

## Review modes

- **Spec.** Read the spec and patch. Check the behaviour, inverse, seams and affected risk paths. Check that reverting the fix would fail the test and that no check was loosened.
- **Outcome.** Give a separate reviewer the original goal, the repository and the candidate change. Leave out the plan, spec and builder's account. Check the actual entry point and ask what the plan missed. Run the real path in a throwaway worktree where possible.
- **Combined.** Use one brief that checks the spec and the real outcome. For high-impact code, use a stronger reviewer and name the specific failures it must try, such as a wrong amount, a denied request or a failed restore.

The reviewer writes only its verdict. Its first line is `VERDICT: PASS`, `VERDICT: PASS WITH FOLLOW-UPS` or `VERDICT: FIX`. Record the head and rank findings with file and line, evidence and the fix. FIX means at least one P1. Give P2 and P3 follow-ups an owner and a later part.

## When a fix needs another read

- Fix P1s inside the landing and let CI judge the fixes. Do not start another review round.
- The one exception is a P1 in security, money, auth, data integrity or a production incident. The same reviewer checks only the fix once and runs the affected check on the candidate. If the finding is still open, hold the landing and return it to design.
- Demonstrate P1s where a test, request or script can show the fault. Put an unproven concern in a question or P2 with the check that could settle it. Use [interrogate](techniques.md#interrogate) in a scheduled spec, outcome or design review.

## Keep reviews focused

Batch small parts that call for review into one session. Record a verdict for each. Use lighter models for routine reviews. Scope each brief to the few checks that matter. When a finding repeats, add a test, lint rule or CI check.

Carry verdicts into a train when the reviewed patches match. Record any later P1 fixes and the gate that cleared them. Test integration changes on the candidate tree and leave the full suite to CI.
