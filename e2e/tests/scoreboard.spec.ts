import { test, expect } from '@playwright/test';

// Seeded users: id 1 is Morgan Manager (admin), id 3 is a consultant
// (see backend/app/seed.py).
const ADMIN_USER_ID = '1';
const CONSULTANT_USER_ID = '3';

test.describe('Scoreboard', () => {
  test('a consultant sees the revealed game with a real box score', async ({ page }) => {
    await page.addInitScript(
      (id) => localStorage.setItem('currentUserId', id),
      CONSULTANT_USER_ID,
    );
    await page.goto('/');

    const section = page.locator('section', { has: page.getByText("Today's games") });
    await expect(section).toBeVisible();

    // The seed script reveals exactly one workday's games; at least one
    // game button should show real numeric scores rather than the hidden
    // placeholder.
    await expect(section.getByText(/Final ·/).first()).toBeVisible();

    // The box score renders below once a revealed game is auto-selected.
    await expect(page.getByText('Box score')).toBeVisible();
    await expect(page.getByRole('columnheader', { name: '11am' }).first()).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Pts' }).first()).toBeVisible();
  });

  test('an admin can see hidden game scores that a consultant cannot', async ({
    page,
    request,
  }) => {
    const gamesResponse = await request.get('http://localhost:8000/games', {
      headers: { 'X-User-Id': ADMIN_USER_ID },
    });
    const games = await gamesResponse.json();
    const hiddenGame = games.find((g: { revealed: boolean }) => !g.revealed);
    test.skip(!hiddenGame, 'no scheduled-but-unrevealed game in the seeded data');

    const asConsultant = await request.get(
      `http://localhost:8000/games/${hiddenGame.id}/box-score`,
      { headers: { 'X-User-Id': CONSULTANT_USER_ID } },
    );
    expect(asConsultant.status()).toBe(403);

    const asAdmin = await request.get(
      `http://localhost:8000/games/${hiddenGame.id}/box-score`,
      { headers: { 'X-User-Id': ADMIN_USER_ID } },
    );
    expect(asAdmin.status()).toBe(200);
  });
});
