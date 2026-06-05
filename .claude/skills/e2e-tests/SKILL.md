---
name: e2e-tests
description: Run end-to-end tests to verify the changes work correctly in a full system context
---

You are the e2e test agent. Your job is to run end-to-end tests using Playwright and ensure the implemented changes work correctly in a full system context.

The e2e project lives at `e2e/` in the workspace root.

## Process

1. Check if e2e tests exist in the project:
   - Look in `e2e/` for `tests/`, `package.json`, and `playwright.config.ts`
   - Check `e2e/package.json` for an e2e test script

2. If Playwright is NOT installed or configured:
   - Install Playwright:
   ```bash
   cd e2e
   npm init -y
   npm install -D @playwright/test
   npx playwright install
   ```
   - If `npx playwright install` fails with a TLS / certificate error (common behind a corporate proxy), use the helper script:
     ```bash
     cd e2e
     # NODE_EXTRA_CA_CERTS should point at a CA bundle the user has on disk
     NODE_EXTRA_CA_CERTS="$NODE_EXTRA_CA_CERTS" node "$(git rev-parse --show-toplevel)/.claude/skills/e2e-tests/scripts/install-browsers.js"
     ```
     See `.claude/skills/e2e-tests/scripts/install-browsers.js` for supported env vars (`NODE_EXTRA_CA_CERTS`, `PLAYWRIGHT_INSECURE_TLS`, `PLAYWRIGHT_BROWSER`). If `NODE_EXTRA_CA_CERTS` isn't set in the user's environment, ask them for the path to their CA bundle rather than guessing.
   - Create `playwright.config.ts` with video recording enabled (see configuration below)
   - Create `e2e/tests` directory
   - Emit `E2E_SETUP_COMPLETE: Playwright installed and configured` and continue on to the next step do not stop.

3. Determine if new e2e tests are needed:
   - Review the task requirements and acceptance criteria
   - If the task involves new user-facing features, UI changes, or user workflows:
     - Create new e2e tests that cover the feature end-to-end
     - Place tests in `e2e/tests/` following naming convention: `feature-name.spec.ts`
   - If the task is backend-only, refactoring, or doesn't affect user workflows:
     - Skip new test creation

4. Verify Playwright is configured for video recording:
   - Check `playwright.config.ts` for `video: 'on'` (to retain all videos)
   - Ensure the `outputDir` resolves to `e2e/test-results` (use a relative path like `./test-results`)
   - If configuration is missing or incorrect, update it (see configuration section)

5. If e2e tests exist, run them:

   First, clean previous test artifacts:
   ```bash
   cd e2e
   rm -rf test-results playwright-report
   ```

   Then run the tests:
   ```bash
   cd e2e
   npm run test:e2e
   ```

   Or if `test:e2e` script doesn't exist:
   ```bash
   cd e2e
   npx playwright test
   ```

6. Analyze test results:
   - If all tests pass, proceed to step 8
   - If tests fail, analyze the failures and check local logs (frontend and backend)

7. If tests fail:
   - Review any videos in `e2e/test-results` for visual debugging
   - Check trace files if available
   - Determine if the failure is due to the new changes or existing issues
   - Fix the issues (either in the tests or in the implementation)
   - Re-run tests until all pass
   - If tests cannot be fixed, output `E2E_TESTS_BLOCKED: <reason>` and stop

8. Stage test results (from the workspace root):
   ```bash
   git add e2e/test-results/
   ```
   This preserves evidence of test execution and aids in debugging and verification.

9. Emit test results:
   - If new tests were created: Emit `E2E_TESTS_PASSED: <number> tests passed (<number> new tests created), results committed to e2e/test-results` and continue on to the next step in the workflow - do not stop.
   - If no new tests: Emit `E2E_TESTS_PASSED: <number> tests passed, results committed to e2e/test-results` and continue on to the next step in the workflow - do not stop.

## Special Cases

If e2e tests require infrastructure that's not available (databases, external services):
- Document the required infrastructure
- Emit `E2E_TESTS_SKIPPED: required infrastructure not available — <details>` and continue on to the next step in the workflow - do not stop.
- This is not a blocker; the workflow can continue

If this is the first time setting up e2e tests:
- Follow step 2 to install and configure Playwright
- Create at least one basic smoke test to verify the setup
- Proceed with running tests

## Playwright Configuration Requirements

A canonical config lives at `.claude/skills/e2e-tests/assets/playwright.config.ts`. Copy it into the e2e project when bootstrapping:

```bash
cp .claude/skills/e2e-tests/assets/playwright.config.ts e2e/playwright.config.ts
```

If the e2e project already has a `playwright.config.ts`, verify it has these required settings (otherwise update it):
- `video: 'on'` — record videos for all tests, both passing and failing
- `trace: 'on'` — record traces for debugging
- `screenshot: 'on'` — take screenshots throughout test execution
- `outputDir: './test-results'` — relative to the e2e/ directory

## E2E Test Creation Guidelines

When creating new e2e tests for features:

1. **Test File Naming**: Use descriptive names like `login-flow.spec.ts`, `checkout-process.spec.ts`
2. **Test Structure**: Follow the Arrange-Act-Assert pattern
3. **User Perspective**: Write tests from the end user's perspective
4. **Happy Path First**: Cover the main success scenario before edge cases
5. **Independent Tests**: Each test should be able to run independently
6. **Clear Test Names**: Use descriptive test names that explain what is being tested

Example test template:

```typescript
import { test, expect } from '@playwright/test';

test.describe('Feature Name', () => {
  test('should complete primary user workflow', async ({ page }) => {
    // Arrange: Navigate to starting point
    await page.goto('/');

    // Act: Perform user actions
    await page.click('button[data-testid="action-button"]');
    await page.fill('input[name="field"]', 'value');
    await page.click('button[type="submit"]');

    // Assert: Verify expected outcome
    await expect(page.locator('.success-message')).toBeVisible();
  });
});
```

## Rules

- The e2e project is always at `e2e/` — never look it up from a config file
- Always clean `test-results/` and `playwright-report/` before each run
- All existing e2e tests must pass before proceeding
- Create new e2e tests for new user-facing features, UI changes, or user workflows
- Do NOT create e2e tests for backend-only changes or refactoring
- If tests are flaky, run them multiple times to verify consistency
- Always stage test results (`git add e2e/test-results/`) from the workspace root
- Verify Playwright is configured to record videos for all tests (`video: 'on'`)
