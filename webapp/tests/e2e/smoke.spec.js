import { test, expect } from '@playwright/test';

test('webapp loads without crashing', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await expect(page.locator('html')).toBeAttached();
});
