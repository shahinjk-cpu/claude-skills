---
name: playwright-e2e-automation
description: Architect, write, and execute robust end-to-end (E2E) browser automation tests, regression suites, and user flow verifications using Playwright (TypeScript/JavaScript/Python). Use when writing integration tests, debugging UI flows, testing multi-step forms, testing auth sessions, verifying visual regressions, or generating cross-browser test scripts.
---

# Playwright E2E Automation Skill

Comprehensive guide for architecting, authoring, and maintaining production-grade End-to-End (E2E) tests and browser automation scripts with Playwright.

---

## 1. Core Principles

1. **User-Centric Locators**: Always prefer locators that mimic real human interaction:
   - `getByRole('button', { name: /submit/i })`
   - `getByLabel('Email')`
   - `getByPlaceholder('Enter your password')`
   - `getByText(...)`
   - Avoid brittle CSS (`div > div:nth-child(2) > input`) or XPath selectors unless inspecting third-party legacy iframes.
2. **Auto-Waiting Over Hard Waits**:
   - Playwright automatically waits for elements to be actionable (visible, enabled, stable).
   - **Never** use `page.waitForTimeout(5000)` in production tests. Use web assertions: `await expect(locator).toBeVisible()` or `await page.waitForURL('/dashboard')`.
3. **Isolated Test State (Storage State)**:
   - Log in once in global setup or test fixtures and save state to `storageState.json` to skip repetitive UI logins across hundreds of test specs.
4. **Resilient Network Mocking**:
   - Intercept third-party APIs (Stripe, Twilio, external OAuth) with `page.route()`, while letting core internal API routes run against test environments.

---

## 2. Directory Structure & Architecture

```
e2e/
├── fixtures/
│   └── auth.fixture.ts        # Reusable authenticated page fixture
├── pages/                     # Page Object Model (POM)
│   ├── base.page.ts
│   ├── auth.page.ts
│   └── dashboard.page.ts
├── specs/
│   ├── auth/
│   │   ├── login.spec.ts
│   │   └── signup.spec.ts
│   ├── payments/
│   │   └── checkout.spec.ts
│   └── smoke/
│       └── critical-path.spec.ts
├── global-setup.ts            # Token generation & auth seeding
├── playwright.config.ts       # Cross-browser & viewport matrix
└── tsconfig.json
```

---

## 3. Configuration Best Practices (`playwright.config.ts`)

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e/specs',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10000,
    navigationTimeout: 15000,
  },
  projects: [
    {
      name: 'setup',
      testMatch: /global-setup\.ts/,
    },
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-safari',
      use: {
        ...devices['iPhone 14'],
        storageState: 'e2e/.auth/user.json',
      },
      dependencies: ['setup'],
    },
  ],
});
```

---

## 4. Page Object Model (POM) Pattern

Encapsulate DOM details behind semantic action methods:

```typescript
// e2e/pages/dashboard.page.ts
import { expect, type Locator, type Page } from '@playwright/test';

export class DashboardPage {
  readonly page: Page;
  readonly heading: Locator;
  readonly createProjectBtn: Locator;
  readonly projectModal: Locator;
  readonly projectNameInput: Locator;
  readonly saveBtn: Locator;
  readonly projectCard: (name: string) => Locator;

  constructor(page: Page) {
    this.page = page;
    this.heading = page.getByRole('heading', { level: 1, name: /dashboard/i });
    this.createProjectBtn = page.getByRole('button', { name: /create project/i });
    this.projectModal = page.getByRole('dialog', { name: /new project/i });
    this.projectNameInput = page.getByLabel('Project Name');
    this.saveBtn = page.getByRole('button', { name: /create/i });
    this.projectCard = (name: string) => page.getByRole('article').filter({ hasText: name });
  }

  async goto() {
    await this.page.goto('/dashboard');
    await expect(this.heading).toBeVisible();
  }

  async createProject(name: string) {
    await this.createProjectBtn.click();
    await expect(this.projectModal).toBeVisible();
    await this.projectNameInput.fill(name);
    await this.saveBtn.click();
    await expect(this.projectModal).toBeHidden();
    await expect(this.projectCard(name)).toBeVisible({ timeout: 5000 });
  }
}
```

---

## 5. API Mocking & Network Interception

```typescript
test('handles payment gateway outage gracefully', async ({ page }) => {
  // Mock external Stripe endpoint to return 500
  await page.route('**/v1/payment_intents', async (route) => {
    await route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: { message: 'Service temporarily unavailable' } }),
    });
  });

  await page.goto('/checkout');
  await page.getByRole('button', { name: /pay now/i }).click();

  // Verify toast/alert notification
  const errorAlert = page.getByRole('alert');
  await expect(errorAlert).toContainText(/payment processing failed/i);
});
```

---

## 6. Visual Regression Testing

```typescript
test('landing page visual snapshot matches baseline', async ({ page }) => {
  await page.goto('/');
  // Mask dynamic elements (timestamps, user avatar)
  await expect(page).toHaveScreenshot('landing-page.png', {
    mask: [page.getByTestId('live-clock'), page.getByAltText(/avatar/i)],
    maxDiffPixelRatio: 0.02,
  });
});
```
