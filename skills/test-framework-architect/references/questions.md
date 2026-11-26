# Intake questions

Ask with AskUserQuestion, max 4 questions per call, 2-4 options each (the tool adds "Other"). Where a menu has more than 4 options, split into two questions or put the top 3 as options and cover the rest via "Other" and a short follow-up. Mark multi-select where noted.

Defaults apply when the user says "not sure" / "recommend". Always flag them REVISITABLE.

## Group 1: Application and scope

**Q1. Application type(s)** (multi-select): Web / API / Mobile (native or hybrid) / Desktop
- If more than web+API is chosen, recommend phasing (web+API first). Risk: mobile and desktop need different drivers (Appium, WinAppDriver, Playwright Electron) and device infrastructure.

**Q2. Tech stack under test** (multi-select): React/Vue/Angular SPA / Server-rendered web (Rails, Django, Laravel, .NET MVC) / REST API / GraphQL API / Native Android or iOS / Desktop (Electron, WPF, native) / Other
- Default: SPA + REST API.

**Q3. Test volume**: ~under 100 / 100-500 / 500-2000 / 2000+ / Not sure
- Default: plan for 100-300 in year one; structure must scale to 1000+.

**Q4. Greenfield or migration**: Greenfield / Migrating manual tests (TestRail, Zephyr, spreadsheets) / Both
- Migration adds an import path (CSV or tool export to test skeletons).

## Group 2: Team and environment

**Q5. Language**: TypeScript / Python / Java / C# / Not sure
- Default: TypeScript with Playwright (single language for web+API, strongest tooling). Python is the best alternative for teams that prefer readability.

**Q6. Team size and experience**: Solo new to automation / Solo experienced / 2-5 mixed / 6+ with dedicated SDETs / Mostly manual testers learning to code
- Drives abstraction level: less experienced teams get fewer layers and more comments.

**Q7. Development OS**: macOS / Windows / Linux / Mixed
- Mixed: avoid shell-specific scripts; use cross-platform task runners.

**Q8. CI/CD platform**: GitHub Actions / GitLab CI / Jenkins / Azure DevOps / CircleCI / None yet
- Default: GitHub Actions if the repo is on GitHub, GitLab CI if on GitLab.
- Ask hosted vs self-hosted runners as a follow-up only if relevant to browser install.

**Q9. Integrations** (multi-select): Jira / Zephyr Scale / TestRail / Slack or Teams notifications / Allure or dashboard / None
- Default: None; JUnit XML keeps the door open for all of them.

## Group 3: Constraints and preferences

**Q10. Compliance and security**: None special / Synthetic data only (GDPR/PII) / No cloud services / SOC 2 or audit trail / Secrets from a vault
- Multi-select allowed. Default: none special, but secrets always via environment variables.

**Q11. Environments**: 1 (local/dev) / 2 (dev, staging) / 3 (dev, staging, prod read-only smoke) / 4+
- Default: 3, with prod limited to read-only smoke tests. Flag: never run destructive tests against prod.

**Q12. Parallel execution**: None / 2-4 workers / 5-10 workers or CI sharding / Grid or cloud (Selenium Grid, BrowserStack, Sauce Labs)
- Default: 2-4 workers.

**Q13. Existing standards**: None / BDD-Gherkin required / Existing style guide or linter / Mandated tool
- If a mandated tool or style guide exists, ask the user to name it or point to the file.

**Q14. First delivery target**: 1 week / 2 weeks / 4 weeks / 6+ weeks
- Default: smoke suite in CI within 2 weeks. Under 1 week: cut to Phases 1-5 minimal + one smoke test.

## Group 4: Authentication

**Q15. Auth approach**:
- Real UI login in a setup step, session reused across tests
- API/token login (fastest, bypasses login UI)
- SSO/OAuth/MFA via test identity provider, test accounts, or TOTP
- Mocked auth: stub the auth service or inject a fake session (no real credentials)
- Mix: real login for one dedicated login test, token or mocked auth for everything else (recommended default)
- Flag: mocked auth does not prove the real auth path works; keep at least one real-login test.

## Deferred

**Q16. First two pages and the smoke flow**: asked at Phase 5 step 4 only. Ask the user to name the two pages and key elements (or to paste a URL or HTML so you can inspect it). If they want to decide later, scaffold the page object base and leave a clearly marked TODO for the two examples; do not invent pages.
