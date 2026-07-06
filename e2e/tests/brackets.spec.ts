import { test, expect } from '@playwright/test';

const PLAYER_MANAGER_USER_ID = '2';

test.describe('Brackets', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      (id) => localStorage.setItem('currentUserId', id),
      PLAYER_MANAGER_USER_ID,
    );
    await page.goto('/');
  });

  test('shows this weeks matchups end to end', async ({ page }) => {
    const [response] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/brackets')),
      page.goto('/'),
    ]);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.matchups.length).toBeGreaterThan(0);

    const section = page.locator('section', {
      has: page.getByText("This week's brackets"),
    });
    await expect(section).toBeVisible();
    await expect(section.getByRole('listitem').first()).toBeVisible();
  });
});
