import { test, expect } from '@playwright/test';

test.describe('Weekly calendar', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => localStorage.setItem('currentUserId', '3'));
    await page.goto('/');
  });

  test('shows the week strip with real TimeEntry state per day', async ({ page }) => {
    await expect(page.getByText('Weekly calendar')).toBeVisible();
    await expect(page.locator('button[aria-label*="Mon"]')).toContainText('8h');
    await expect(page.locator('button[aria-label*="Mon"]')).toContainText(/Logged late|On time/);
  });

  test('submitting a day entry creates a TimeEntry via the lifecycle API', async ({ page }) => {
    const fridayTile = page.locator('button[aria-label*="Fri"]');
    await fridayTile.click();

    await page.fill('#weekly-calendar-hours', '6.5');
    await page.fill(
      '#weekly-calendar-description',
      'Verified the weekly calendar day-entry flow end to end.',
    );

    const [logResponse] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/time-entries/log') && r.request().method() === 'POST',
      ),
      page.click('text=Submit entry'),
    ]);
    expect(logResponse.status()).toBe(200);

    await expect(fridayTile).toContainText('6.5h');
  });
});
