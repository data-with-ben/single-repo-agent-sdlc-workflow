import { test, expect } from '@playwright/test';

test.describe('Backend health status', () => {
  test('shows the healthy state when the backend is reachable', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('Backend: ok')).toBeVisible();
  });

  test('shows the unavailable state when the backend is unreachable', async ({ page }) => {
    await page.route('**/health', (route) => route.abort());
    await page.goto('/');
    await expect(page.getByText('Backend unavailable')).toBeVisible();
  });
});
