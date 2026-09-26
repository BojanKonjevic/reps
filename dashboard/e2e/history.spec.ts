import { test, expect, Page, Route } from '@playwright/test';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const dir = dirname(fileURLToPath(import.meta.url));
function fixture(name: string) {
  return JSON.parse(readFileSync(join(dir, 'fixtures', name + '.json'), 'utf8'));
}
function statesFixture(name: string) {
  return JSON.parse(readFileSync(join(dir, 'fixtures', name + '.states.json'), 'utf8'));
}
const rich = fixture('rich');
const spread = fixture('history_spread');
const spreadStates = statesFixture('history_spread');

type Snap = typeof rich;

async function gotoFixture(
  page: Page,
  snapshot: unknown,
  states: unknown,
  asOf: string,
  statesDelayMs = 0
) {
  await page.clock.install({ time: new Date(asOf + 'T12:00:00Z') });
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot) })
  );
  await page.route('**/history-states', async r => {
    if (statesDelayMs) await new Promise(res => setTimeout(res, statesDelayMs));
    if (states === null) {
      await r.fulfill({ status: 404, contentType: 'application/json', body: '{}' });
    } else {
      await r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(states) });
    }
  });
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

const richStates = statesFixture('rich');

test.describe('Temporal context', () => {
  test('lift chart shows events, selection opens before/after detail', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    await page.goto('#/l/bench');
    await expect(page.locator('#chLift')).toBeVisible();
    await expect(page.locator('#liftEvents')).toContainText('Upper A changed');
    await expect(page.locator('#liftEvents')).not.toContainText('Upper B changed');
    await expect(page.locator('#liftEvents')).not.toContainText('Rotation changed');
    await page.locator('#liftEvents button', { hasText: 'Bench goal set' }).click();
    await expect(page.locator('#liftChange')).toContainText('Bench goal set');
    await expect(page.locator('#liftChange')).toContainText('Before');
    await expect(page.locator('#liftChange')).toContainText('After');
    await expect(page.locator('#liftChange')).toContainText('e1RM');
  });

  test('as-of control opens a calendar with event dots', async ({ page }) => {
    await gotoFixture(page, spread, spreadStates, spread.as_of);
    await page.goto('#/l/squat');
    await expect(page.locator('#liftAsof > button')).toContainText('As of Today');
    await expect(page.locator('#liftState')).toHaveCount(0);
    await page.locator('#liftAsof > button').click();
    await expect(page.locator('#liftAsof .asofpop')).toBeVisible();
    await expect(page.locator('#liftAsof .asofpop')).toContainText('September 2026');
    await expect(page.locator('#liftAsof .asofpop button[aria-label="2026-09-10"] .asofdot')).toHaveCount(1);
    await expect(page.locator('#liftAsof .asofpop button[aria-label="2026-09-12"] .asofdot')).toHaveCount(0);
    const box = await page.locator('#liftAsof .asofpop').boundingBox();
    const viewport = page.viewportSize()!;
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width);
  });

  test('any date reconstructs: event date, empty date, between events', async ({ page }) => {
    await gotoFixture(page, spread, spreadStates, spread.as_of);
    await page.goto('#/l/squat');
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="2026-09-12"]').click();
    await expect(page.locator('#liftState')).toContainText('As of Sep 12');
    await expect(page.locator('#liftState')).toContainText('squat · 2 sets');
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="2026-09-05"]').click();
    await expect(page.locator('#liftState')).toContainText('As of Sep 5');
    await expect(page.locator('#liftState')).toContainText('squat · 3 sets');
  });

  test('compare shows only changed fields, or none changed', async ({ page }) => {
    await gotoFixture(page, spread, spreadStates, spread.as_of);
    await page.goto('#/l/squat');
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="2026-09-12"]').click();
    await page.locator('#liftState button', { hasText: 'Compare with today' }).click();
    await expect(page.locator('#liftState')).toContainText('today:');
    await page.locator('#liftState button', { hasText: 'Hide comparison' }).click();
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="2026-09-18"]').click();
    await page.locator('#liftState button', { hasText: 'Compare with today' }).click();
    await expect(page.locator('#liftState')).toContainText('No relevant changes since Sep 18.');
  });

  test('event flows into as-of: detail carries the date', async ({ page }) => {
    await gotoFixture(page, spread, spreadStates, spread.as_of);
    await page.goto('#/l/squat');
    await page.locator('#liftEvents button', { hasText: 'Lower A changed' }).nth(1).click();
    await page.locator('#liftChange button', { hasText: 'View training state' }).click();
    await expect(page.locator('#liftState')).toContainText('Training state');
    await expect(page.locator('#liftAsof > button')).toContainText('Sep 10');
    await page.locator('#liftEvents button', { hasText: 'Lower A changed' }).nth(1).click();
    await expect(page.locator('#liftChange')).toHaveCount(0);
    await expect(page.locator('#chLift')).toBeVisible();
  });

  test('chart markers select the same event as the strip', async ({ page }) => {
    await gotoFixture(page, spread, spreadStates, spread.as_of);
    await page.goto('#/l/squat');
    const box = await page.locator('#chLift').boundingBox();
    expect(box).toBeTruthy();
    // Time scale runs first session (Sep 04) to as-of (Sep 24): Sep 10 sits at 6/20.
    const x = box!.x + 46 + ((box!.width - 54) * 6) / 20;
    await page.mouse.click(x, box!.y + box!.height / 2);
    await expect(page.locator('#liftChange')).toContainText('Lower A changed');
    await expect(
      page.locator('#liftEvents button[aria-pressed="true"]', { hasText: 'Lower A changed' })
    ).toHaveCount(1);
  });

  test('missing evidence reads as not recorded, never invented', async ({ page }) => {
    await gotoFixture(page, spread, spreadStates, spread.as_of);
    await page.goto('#/l/squat');
    await page.locator('#liftEvents button', { hasText: 'Lower A changed' }).first().click();
    await expect(page.locator('#liftChange')).toContainText('Reason');
    await expect(page.locator('#liftChange')).toContainText('Not recorded.');
  });

  test('history loading keeps the chart visible', async ({ page }) => {
    await gotoFixture(page, spread, spreadStates, spread.as_of, 400);
    await page.goto('#/l/squat');
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="2026-09-12"]').click();
    await expect(page.locator('#liftState')).toContainText('Loading historical state…');
    await expect(page.locator('#chLift')).toBeVisible();
    await expect(page.locator('#liftState')).toContainText('squat · 2 sets', { timeout: 5000 });
  });

  test('unavailable states stay unavailable, before-history stays unknown', async ({ page }) => {
    await gotoFixture(page, spread, null, spread.as_of);
    await page.goto('#/l/squat');
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="2026-09-12"]').click();
    await expect(page.locator('#liftState')).toContainText('Historical state unavailable.');
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="Previous month"]').click();
    await expect(page.locator('#liftAsof .asofpop')).toContainText('August 2026');
    const disabled = page.locator('#liftAsof .asofpop button.asofday[disabled]');
    expect(await disabled.count()).toBeGreaterThan(20);
  });

  test('partial reconstruction says so instead of failing', async ({ page }) => {
    const partial = JSON.parse(JSON.stringify(spreadStates));
    partial.states[1].program[0].known = false;
    await gotoFixture(page, spread, partial, spread.as_of);
    await page.goto('#/l/squat');
    await page.locator('#liftAsof > button').click();
    await page.locator('#liftAsof .asofpop button[aria-label="2026-09-12"]').click();
    await expect(page.locator('#liftState')).toContainText(
      'Some training state could not be reconstructed for Sep 12.'
    );
    await expect(page.locator('#liftState')).toContainText('quads');
  });

  test('unknown history is communicated, not invented', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    await page.goto('#/l/bench');
    await expect(page.locator('#liftHistNote')).toContainText('earlier changes were not recorded');
  });

  test('home shows recent changes with inline detail', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    await expect(page.locator('#changedWrap h2')).toContainText('What changed');
    await expect(page.locator('#changedCard')).toContainText('Upper A changed');
    await page.locator('#changedCard button', { hasText: 'Chest priority changed' }).click();
    await expect(page.locator('#changedCard')).toContainText('Before');
    await expect(page.locator('#changedCard')).toContainText('Reason');
  });

  test('muscle page annotates volume with priority changes', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    await page.goto('#/m/chest');
    await expect(page.locator('#chMusVol')).toBeVisible();
    await expect(page.locator('#musEvents')).toContainText('Chest priority changed');
    await page.locator('#musEvents button', { hasText: 'Chest priority changed' }).click();
    await expect(page.locator('#musChange')).toContainText('Reason');
    await expect(page.locator('#musProv summary')).toContainText('How this is calculated');
    await page.locator('#musProv summary').click();
    await expect(page.locator('#musProv')).toContainText('Sources');
  });

  test('consistency days explain expected, actual, classification, rotation', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    await page.locator('#adhCard .dtstrip button').first().click();
    await expect(page.locator('#adhDetail')).toContainText('Expected:');
    await expect(page.locator('#adhDetail')).toContainText('Status:');
    await expect(page.locator('#adhDetail')).toContainText('Rotation at this time:');
  });

  test('bodyweight points show nearby training changes', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    await expect(page.locator('#chBw')).toBeVisible();
    const bw = page.locator('#chBw');
    await bw.scrollIntoViewIfNeeded();
    const box = await bw.boundingBox();
    expect(box).toBeTruthy();
    await page.mouse.click(box!.x + box!.width - 18, box!.y + box!.height / 2);
    await expect(page.locator('#bwNear')).toBeVisible();
  });

  test('history page lists, filters, and details every change', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
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
    await expect(page.locator('#histList')).toContainText('Rotation changed');
    await page.locator('#histList .histrow button', { hasText: 'Bench goal set' }).click();
    await expect(page.locator('#histList')).toContainText('Before');
  });

  test('goal cards preserve historical targets', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    await expect(page.locator('#goalGrid')).toContainText('target e1RM');
  });

  test('no accidental horizontal scrolling', async ({ page }) => {
    await gotoFixture(page, rich, richStates, rich.as_of);
    for (const hash of ['#/', '#/l/bench', '#/m/chest', '#/history', '#/program']) {
      await page.goto(hash);
      await page.waitForLoadState('networkidle');
      const overflow = await page.evaluate(
        () => document.scrollingElement!.scrollWidth - window.innerWidth
      );
      expect(overflow).toBeLessThanOrEqual(1);
    }
  });
});
