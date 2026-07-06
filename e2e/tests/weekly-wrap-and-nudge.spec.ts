import { test, expect } from '@playwright/test';

// Seeded users: id 2 is Riley Player-Manager, who the seed script gives
// two real demo holdings (see backend/app/seed.py), making them eligible
// to nudge those consultants.
const PLAYER_MANAGER_USER_ID = '2';

test.describe('Nudge', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(
      (id) => localStorage.setItem('currentUserId', id),
      PLAYER_MANAGER_USER_ID,
    );
    await page.goto('/');
  });

  test('sending a nudge to a held consultant succeeds', async ({ page }) => {
    await expect(page.getByRole('button', { name: 'Nudge' }).first()).toBeVisible();

    const [response] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes('/nudge') && r.request().method() === 'POST',
      ),
      page.getByRole('button', { name: 'Nudge' }).first().click(),
    ]);
    expect(response.status()).toBe(200);
    await expect(page.getByText('Nudge sent!')).toBeVisible();
  });
});

test.describe('Weekly wrap', () => {
  test('the endpoint returns a bundled shape for a past week', async ({ request }) => {
    const weekStart = new Date();
    weekStart.setDate(weekStart.getDate() - 7);
    const response = await request.get('http://localhost:8000/weekly-wrap', {
      params: { week_start: weekStart.toISOString().slice(0, 10) },
      headers: { 'X-User-Id': PLAYER_MANAGER_USER_ID },
    });
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('team_records');
    expect(body).toHaveProperty('biggest_market_swing');
    expect(body).toHaveProperty('star_performer');
  });
});
