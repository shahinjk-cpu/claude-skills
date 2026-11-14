---
name: playwright-cli
description: >
  High-performance headless and headed browser automation using Playwright CLI. Run end-to-end tests, capture screenshots, trace network requests, and record video sessions.
metadata:
  version: "1.0.0"
  category: testing_qa
  triggers: playwright-cli, browser automation, e2e testing, headless browser, web testing
---

# Playwright CLI — Resilient Browser Automation

Automates web interactions, end-to-end testing, and visual regression tests using Playwright.

## Best Practices
- Always use auto-waiting locators (`page.getByRole`, `page.getByText`) instead of hardcoded timeouts.
- Capture full-page screenshots for visual audits: `page.screenshot(path="out.png", full_page=True)`.
- Use isolated browser contexts to prevent shared session pollution.
