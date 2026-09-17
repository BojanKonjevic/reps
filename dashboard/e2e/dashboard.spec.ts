import { test, expect } from '@playwright/test';

test.describe('Dashboard', () => {
  test('loads and shows dashboard title', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1')).toContainText('Training dashboard');
  });

  test('shows estimated 1RM trend section', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h2:has-text("Estimated 1RM trend")')).toBeVisible();
  });

  test('shows weekly volume by muscle section', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h2:has-text("Weekly volume by muscle")')).toBeVisible();
  });

  test('shows bodyweight section', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h2:has-text("Bodyweight")')).toBeVisible();
  });

  test('shows training calendar', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h2:has-text("Training calendar")')).toBeVisible();
  });

  test('shows best sets table', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#prs')).toBeVisible();
  });

  test('navigates calendar prev/next', async ({ page }) => {
    await page.goto('/');
    const prev = page.locator('#calPrev');
    const next = page.locator('#calNext');
    await expect(prev).toBeVisible();
    await expect(next).toBeVisible();
  });

  test('dashboard visual regression - desktop', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.setViewportSize({ width: 1280, height: 720 });
    await expect(page).toHaveScreenshot('dashboard-desktop.png', { maxDiffPixels: 100 });
  });

  test('dashboard visual regression - mobile', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page).toHaveScreenshot('dashboard-mobile.png', { maxDiffPixels: 100 });
  });
});
