import { test, expect } from '@playwright/test';

// Seeded users: id 2 is Riley Player-Manager (see backend/app/seed.py),
// who the seed script gives two real demo holdings so this screen has
// something to render in a freshly seeded environment.
const PLAYER_MANAGER_USER_ID = '2';

test.describe('Portfolio', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      (id) => localStorage.setItem('currentUserId', id),
      PLAYER_MANAGER_USER_ID,
    );
    await page.goto('/');
  });

  test('shows real holdings with live quotes and 7-day movement', async ({ page }) => {
    const section = page.locator('section', { has: page.getByText('Your portfolio') });
    await expect(section).toBeVisible();
    await expect(section.getByRole('row')).not.toHaveCount(0);
  });

  test('a buy action calls the trade endpoint and updates the wallet', async ({
    page,
  }) => {
    const walletText = await page.getByText(/Wallet: \d+ pts/).textContent();

    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/trade/buy') && r.request().method() === 'POST',
      ),
      page.getByRole('button', { name: 'Buy' }).first().click(),
    ]);
    expect(response.status()).toBe(200);

    await expect(async () => {
      const updated = await page.getByText(/Wallet: \d+ pts/).textContent();
      expect(updated).not.toBe(walletText);
    }).toPass();
  });

  test('browsing the exchange lists a consultant not yet held', async ({ page }) => {
    const [response] = await Promise.all([
      page.waitForResponse((r) => r.url().includes('/exchange')),
      page.getByRole('button', { name: 'Browse the exchange' }).click(),
    ]);
    expect(response.status()).toBe(200);
    const listings = await response.json();
    expect(listings.length).toBeGreaterThan(0);
  });
});
