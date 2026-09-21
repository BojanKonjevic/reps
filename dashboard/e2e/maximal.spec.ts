import { test, expect, Page } from '@playwright/test';
import * as fs from 'node:fs';

const SNAP = JSON.parse(fs.readFileSync('/tmp/mock_snapshot.json', 'utf8'));

async function gotoMock(page: Page) {
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SNAP) })
  );
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

test.describe('maximal mock', () => {
  test('dash sections render', async ({ page }) => {
    await gotoMock(page);
    await expect(page.locator('#nowLines')).toContainText('Focus:');
    await expect(page.locator('#rotLine')).toContainText('Rotating');
    await expect(page.locator('#goalGrid .goalcard').first()).toBeVisible();
    await expect(page.locator('#progTable tr')).toHaveCount(7);
    const firstMini = await page.locator('#trendGrid .mini a').first().textContent();
    if (['incline barbell bench press', 'leg press'].indexOf(firstMini || '') < 0)
      throw new Error('goal lifts should lead the trends, got ' + firstMini);
    await expect(page.locator('#legMus a.focus').first()).toBeVisible();
    await page.screenshot({ path: '/tmp/max-dash.png', fullPage: true });
  });

  test('trend filters isolate and combine', async ({ page }) => {
    await gotoMock(page);
    await page.locator('#trendFacets button', { hasText: /^Goals$/ }).click();
    await expect(page.locator('#trendGrid .mini')).toHaveCount(2);
    await page.locator('#trendFacets button', { hasText: /^Stalling$/ }).click();
    const n = await page.locator('#trendGrid .mini').count();
    if (n <= 2) throw new Error('combining filters should widen, got ' + n);
    await page.locator('#trendSearch').fill('press');
    const m = await page.locator('#trendGrid .mini').count();
    if (m >= n) throw new Error('search should narrow, got ' + m);
    await page.locator('#trendFacets button', { hasText: /^Reset$/ }).click();
    await expect(page.locator('#trendGrid .mini').first()).toBeVisible();
  });

  test('volume segment taps through to muscle page', async ({ page }) => {
    await gotoMock(page);
    await page.locator('#chMus').scrollIntoViewIfNeeded();
    const box = await page.locator('#chMus').boundingBox();
    if (!box) throw new Error('no volume canvas');
    await page.mouse.click(box.x + 80, box.y + box.height - 60);
    await expect(page.locator('#viewMuscle')).toBeVisible();
  });

  test('goal hover shows logged weight and plan', async ({ page }) => {
    await gotoMock(page);
    await page.locator('#goalGrid canvas').first().scrollIntoViewIfNeeded();
    const box = await page.locator('#goalGrid canvas').first().boundingBox();
    if (!box) throw new Error('no goal canvas');
    await page.mouse.move(box.x + 60, box.y + box.height / 2);
    await expect(page.locator('.tip')).toBeVisible();
    await expect(page.locator('.tip')).toContainText('plan');
  });

  test('muscle page shows bands and contributors', async ({ page }) => {
    await gotoMock(page);
    await page.locator('#legMus a').first().click();
    await expect(page.locator('#viewMuscle')).toBeVisible();
    await expect(page.locator('#musLegend .row').first()).toBeVisible();
    await expect(page.locator('#musLegend')).toContainText('%');
    await page.waitForTimeout(300);
    await page.screenshot({ path: '/tmp/max-muscle.png', fullPage: false });
  });

  test('program page renders full split', async ({ page }) => {
    await gotoMock(page);
    await page.locator('#progLink').click();
    await expect(page.locator('#viewProgram')).toBeVisible();
    await expect(page.locator('#progGrid .daypanel')).toHaveCount(6);
    await expect(page.locator('#progGrid table tbody tr').first()).toBeVisible();
    await page.waitForTimeout(300);
    await page.screenshot({ path: '/tmp/max-program.png', fullPage: true });
  });

  test('lift view with trajectory', async ({ page }) => {
    await gotoMock(page);
    await page.locator('#trendGrid .mini a').first().click();
    await expect(page.locator('#viewLift')).toBeVisible();
    await expect(page.locator('#liftMuscles a').first()).toBeVisible();
    await expect(page.locator('#liftPRs .tl-item').first()).toBeVisible();
    await page.waitForTimeout(400);
    await page.screenshot({ path: '/tmp/max-lift.png', fullPage: false });
  });

  test('session view with slot', async ({ page }) => {
    await gotoMock(page);
    await page.locator('.cal a.cd.t').last().click();
    await expect(page.locator('#viewSession')).toBeVisible();
    await page.waitForTimeout(300);
    await page.screenshot({ path: '/tmp/max-session.png', fullPage: true });
  });
});
