import { test, expect, Page } from '@playwright/test';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const dir = dirname(fileURLToPath(import.meta.url));
function fixture(name: string) {
  return JSON.parse(readFileSync(join(dir, 'fixtures', name + '.json'), 'utf8'));
}
const rich = fixture('rich');

type Snap = typeof rich;

async function gotoFixture(page: Page, snapshot: unknown, asOf: string) {
  await page.clock.install({ time: new Date(asOf + 'T12:00:00Z') });
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot) })
  );
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

test.describe('Temporal context', () => {
  test('lift chart shows events, selection opens before/after detail', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/l/bench');
    await expect(page.locator('#chLift')).toBeVisible();
    await expect(page.locator('#liftEvents')).toContainText('Upper A changed');
    await expect(page.locator('#liftEvents')).not.toContainText('Upper B changed');
    await page.locator('#liftEvents button', { hasText: 'Bench goal set' }).click();
    await expect(page.locator('#liftChange')).toContainText('Bench goal set');
    await expect(page.locator('#liftChange')).toContainText('Before');
    await expect(page.locator('#liftChange')).toContainText('After');
    await expect(page.locator('#liftChange')).toContainText('e1RM');
  });

  test('as-of control defaults to today and selects event dates', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/l/bench');
    await expect(page.locator('#liftAsof button', { hasText: 'Today' })).toHaveAttribute(
      'aria-pressed',
      'true'
    );
    await expect(page.locator('#liftState')).toHaveCount(0);
    await page.locator('#liftAsof button:not(:has-text("Today"))').first().click();
    await expect(page.locator('#liftState')).toContainText('Training state');
    await expect(page.locator('#liftState')).toContainText('Compare with today');
  });

  test('as-of state reconstructs the training state in effect then', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/l/bench');
    await page.locator('#liftEvents button', { hasText: 'Upper A changed' }).first().click();
    await page.locator('#liftChange button', { hasText: 'View training state' }).click();
    await expect(page.locator('#liftState')).toContainText('Training state');
    await expect(page.locator('#liftState')).toContainText('bench');
    await page.locator('#liftState button', { hasText: 'Compare with today' }).click();
    await expect(page.locator('#liftState')).toContainText('today:');
  });

  test('unknown history is communicated, not invented', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/l/bench');
    await expect(page.locator('#liftHistNote')).toContainText('earlier changes were not recorded');
  });

  test('home shows recent changes with inline detail', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#changedWrap h2')).toContainText('What changed');
    await expect(page.locator('#changedCard')).toContainText('Upper A changed');
    await page.locator('#changedCard button', { hasText: 'Chest priority changed' }).click();
    await expect(page.locator('#changedCard')).toContainText('Before');
    await expect(page.locator('#changedCard')).toContainText('unset');
  });

  test('muscle page annotates volume with priority changes', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/m/chest');
    await expect(page.locator('#chMusVol')).toBeVisible();
    await expect(page.locator('#musEvents')).toContainText('Chest priority changed');
    await page.locator('#musEvents button', { hasText: 'Chest priority changed' }).click();
    await expect(page.locator('#musChange')).toContainText('unset');
    await expect(page.locator('#musProv summary')).toContainText('How this is calculated');
    await page.locator('#musProv summary').click();
    await expect(page.locator('#musProv')).toContainText('Sources:');
  });

  test('consistency days explain expected, actual, and classification', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.locator('#adhCard .dtstrip button').first().click();
    await expect(page.locator('#adhDetail')).toContainText('Expected:');
    await expect(page.locator('#adhDetail')).toContainText('Status:');
  });

  test('bodyweight points show nearby training changes', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#chBw')).toBeVisible();
    const bw = page.locator('#chBw');
    await bw.scrollIntoViewIfNeeded();
    const box = await bw.boundingBox();
    expect(box).toBeTruthy();
    await page.mouse.click(box!.x + box!.width - 18, box!.y + box!.height / 2);
    await expect(page.locator('#bwNear')).toBeVisible();
  });

  test('history page lists, filters, and details every change', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/history');
    await expect(page.locator('#viewHistory h1')).toContainText('History');
    await expect(page.locator('#histList .histrow')).toHaveCount(rich.history.length);
    const goals = rich.history.filter((e: Snap['history'][number]) => e.domain === 'goal').length;
    expect(goals).toBeGreaterThan(0);
    await page.locator('#histFilters button', { hasText: 'Goal' }).click();
    await expect(page.locator('#histList .histrow')).toHaveCount(rich.history.length - goals);
    await expect(page.locator('#histList')).not.toContainText('Bench goal set');
    await page.locator('#histFilters button', { hasText: 'Goal' }).click();
    await expect(page.locator('#histList .histrow')).toHaveCount(rich.history.length);
    await page.locator('#histList .histrow button', { hasText: 'Bench goal set' }).click();
    await expect(page.locator('#histList')).toContainText('Before');
  });

  test('goal cards preserve historical targets', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#goalGrid')).toContainText('target e1RM');
  });

  test('no accidental horizontal scrolling', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    for (const hash of ['#/', '#/l/bench', '#/m/chest', '#/history', '#/program']) {
      await page.goto(hash);
      await page.waitForLoadState('networkidle');
      // scrollWidth past innerWidth is the horizontally scrollable case;
      // clientWidth is smaller whenever a vertical scrollbar is present.
      const overflow = await page.evaluate(
        () => document.scrollingElement!.scrollWidth - window.innerWidth
      );
      expect(overflow).toBeLessThanOrEqual(1);
    }
  });
});
