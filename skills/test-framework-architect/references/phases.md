# Phase specifications

Each phase: present plan, get approval, produce output, end with `Ready to move to Phase N+1? Or would you like to adjust anything?`

## Phase 1: Requirements document
- Max 1 page, summarising intake answers (from `docs/decisions.md`).
- Include a **Non-Goals** section so scope is explicit (for example: performance testing, visual regression, mobile in v1).
- List every REVISITABLE default.
- Ask the user to confirm or correct.

## Phase 2: Tool selection
Present a table: `Layer | Recommended | Alternative | Why`. Layers: browser/mobile automation, test runner, API testing (if applicable), language, reporting, data management. Use `stack-matrix.md`. Confirm each choice. If the user is unsure, recommend the most maintainable option for a small-to-medium team. State the main downside of each recommendation.

## Phase 3: Architecture and design pattern
- Recommend one of Modular, Data-Driven, Keyword-Driven, Hybrid; justify using team size and scale.
- Produce a Mermaid diagram: tests -> page objects/components -> driver; data in (config, fixtures, factories); results out (JUnit XML, HTML, logs).
- Explain: Page Object Model, explicit waits, test independence, separation of concerns.

## Phase 4: Project structure
Generate the full tree with a one-line comment per folder and key file. Include `config/`, `src/pages/`, `src/components/`, `src/api/`, `src/utilities/`, `tests/` (subdivided by type: smoke, regression, api, ...), `data/`, `reports/`, plus tool files (package.json, playwright.config.ts, pytest.ini, build.gradle, ...). Ask for adjustments before creating any files. Then create the skeleton.

## Phase 5: Core infrastructure (confirm between each sub-step)
1. **Configuration**: environments, credentials (env vars only), timeouts; show format and loader.
2. **Base test setup**: browser/driver lifecycle, teardown, screenshot (and trace) on failure.
3. **Page object base class**: click, fill, waitForVisible, getByText/getByRole, etc.
4. **Two example page objects**: ask the user now for page names and key elements (Q16); never invent pages.
5. **Data management**: CSV/JSON/DB loading, factories, fixtures for test isolation.
6. **Reporting**: JUnit XML plus HTML report configuration.
7. **Logging**: structured, with timestamps, test name, step-level detail.
Wire auth per the user's Q15 answer (session reuse, token, or mock).

## Phase 6: First test scripts
Write 3 tests: one smoke (single happy path, 3-5 steps), one data-driven (3+ data sets), one negative/edge case. Rules: one assertion per test (max 3 tightly related), no hardcoded values (config or data files), explicit waits only, accessible locators (role, label, text) before CSS/XPath, descriptive sentence-style names. Run each test if the environment allows. After each, ask: "Does this match how you'd actually test this flow? What's missing?"

**Failure-artifact check (after the 3 tests pass, before Phase 7):** prove the failure path works, because a passing suite never exercises it. Tell the user you're doing this, then:
1. Add a temporary spec with one test that fails on purpose (for example expect a value that is certainly wrong). Name it so it cannot be mistaken for a real test, for example `zz-deliberate-failure.spec`, and tag it so it is easy to remove.
2. Run it alone and confirm: a non-zero exit code; a screenshot and a trace exist under the output folder; the JUnit XML has a `<failure>` entry and a non-zero `failures` count; the HTML report was generated. Open the screenshot and confirm it shows the real failure state.
3. Confirm the CI config uploads the artifact folders even on failure (`if: always()` or the platform equivalent).
4. Delete the temporary spec and its output, re-run the full suite, and confirm it passes and that passing tests leave no failure artifacts.
Report what you saw, including anything you could not verify (for example the CI upload, which needs a real run). Never leave the failing test in the repo.

Lessons from the dry run (apply when generating code):
- Run `tsc --noEmit` (or the language's type/lint check) and the tests themselves before presenting; show the real pass/fail output.
- Data-driven test titles are built from a data field; write the data names so the sentence reads naturally (for example avoid "with with digits").
- Add `.gitignore` (node_modules, reports, test-results, .env) and pin the runtime version (`engines` or `.nvmrc`) in Phase 4.
- Confirm `reports/junit.xml` and `reports/html/` exist after a run; some wrappers or output filters hide reporter output, so check the files, not only the console.

## Phase 7: CI/CD integration
Produce the pipeline file for the chosen platform. Requirements: trigger on every PR to main; smoke on PR (< 10 min); full regression on merge to staging (< 40 min); fail on any test failure; upload reports as artifacts; environment config via environment variables; parallelism if the user chose it. Show what the pipeline output looks like on success and on failure. Validate YAML syntax before presenting. For GitHub Actions, start from `ci-github-actions.yml` (verified: smoke job on PR, 3-way sharded regression on push to staging, `if: always()` artifact upload, env via repo variables) and adapt it to the user's runtime and worker choice. State plainly that the pipeline itself can only be proven by pushing it to a real repo.

## Phase 8: Maintenance and governance
One-page Framework Owner's Guide: checklists for adding a test, page object, and environment; flaky-test process (diagnose, fix or quarantine, document); updating when the app changes; recommended review cadence. Plus a lightweight PR code-review checklist for framework changes.

## Final deliverable
Single consolidated `README.md`: clone and run locally in under 5 minutes, architecture at a glance, how to add a first test following conventions. Verify the quick-start commands.
