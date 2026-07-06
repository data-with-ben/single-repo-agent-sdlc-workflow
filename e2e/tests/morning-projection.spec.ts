import { test, expect } from '@playwright/test';

test.describe('Morning projection', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('currentUserId', '3'));
    await page.goto('/');
  });

  test('shows assigned clients with an open row to project hours', async ({ page }) => {
    const section = page.locator('section', { has: page.getByText('Project your day') });
    await expect(section).toBeVisible();
    await expect(section.getByText('Acme Corp')).toBeVisible();
  });

  test('submitting a projection calls the lifecycle project endpoint', async ({ page }) => {
    const hoursInput = page.getByLabel('Planned hours for Acme Corp');
    await hoursInput.fill('6');

    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/time-entries/project') && r.request().method() === 'POST',
      ),
      page.getByRole('button', { name: 'Project' }).first().click(),
    ]);
    expect(response.status()).toBe(200);
  });
});
