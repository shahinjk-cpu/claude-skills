# Stack matrix

Defaults for Phase 2. Verify current versions and docs before pinning; do not rely on memory for version numbers.

## Web UI

| Language | Recommended | Alternative | Trade-off |
|---|---|---|---|
| TypeScript | Playwright Test | Cypress | Cypress has a friendly runner but is weaker for multi-tab/multi-origin and limits browsers; Playwright has built-in parallelism, tracing, auto-wait |
| Python | Playwright + pytest | Selenium + pytest | Selenium has the widest ecosystem and legacy grid support but is slower and needs more explicit wait handling |
| Java | Playwright for Java + JUnit 5 | Selenium + TestNG | Selenium is the enterprise standard; Playwright is faster to stabilise |
| C# | Playwright for .NET + NUnit | Selenium + NUnit | Same as above |

Selenium is preferred only when the user needs a mandated grid, legacy browser support, or has an existing Selenium investment.

### Additional web stacks

| Stack | Use when | Trade-off |
|---|---|---|
| Cypress (TypeScript) | Front-end team owns the tests and wants the interactive runner and time-travel debugging | Single-origin focus, no real multi-tab, fewer browsers, parallelism needs Cypress Cloud or a third-party tool |
| Robot Framework (+ Browser library, which wraps Playwright) | Non-coding testers write keyword-style scenarios, or the org already standardises on Robot | Keyword layer adds maintenance cost; custom logic needs Python libraries; slower to debug than native code |
| Kotlin (Playwright for Java + JUnit 5, or Selenium + JUnit 5) | JVM shop that prefers Kotlin; reuses the Java bindings | Smaller community examples; the Playwright Java API is used through Kotlin, so docs are in Java |
| Ruby (Capybara + RSpec) | Existing Rails or Ruby team | Slower and less actively developed for modern browser features than Playwright |

For Robot Framework and Kotlin, still map every Phase 5 sub-step (config, fixtures or setup/teardown, base page, data, reporting, logging) onto the stack's native equivalents, and tell the user where the mapping is loose. Robot produces `output.xml`, `log.html` and `report.html`; convert or configure JUnit XML output (`--xunit`) so CI treats results the same way. Verify failure artifacts per the Phase 6 failure-artifact check.

## API
| Language | Recommended | Alternative |
|---|---|---|
| TypeScript | Playwright APIRequestContext | supertest, axios + Vitest |
| Python | requests/httpx + pytest | Playwright API |
| Java | RestAssured | Playwright API |
| C# | RestSharp or HttpClient | Playwright API |
| Kotlin | RestAssured (Kotlin extensions) | Ktor client |
| Robot Framework | RESTinstance or RequestsLibrary | Browser library's HTTP keywords |

GraphQL: same clients with query helpers; add schema or contract checks if a schema is available.

## Mobile (separate package, later phase)
Appium 2 with WebdriverIO (TypeScript) or the language-native client. Alternatives: Maestro (simple flows), Detox (React Native). Flag: needs emulators/devices and signed builds.

## Desktop (separate package, later phase)
Electron: Playwright's Electron support. Windows native: WinAppDriver or FlaUI. Flag: CI needs a Windows runner with a display session.

## Reporting
JUnit XML (machine-readable, always) + built-in HTML report. Optional: Allure for trends and attachments. Alternative for Python: pytest-html.

## Data management
JSON/CSV files under `data/` for static sets; factories (for example faker-based) for generated data; per-test cleanup or unique data for isolation. Keep secrets out of data files.

## Pattern recommendation
| Team and scale | Pattern |
|---|---|
| Small team, < 300 tests | Modular (POM + fixtures) |
| Same flows with many data variants | Hybrid: modular core + data-driven tests |
| Non-coding testers write scenarios | Keyword-driven or BDD layer on top (flag maintenance cost) |
