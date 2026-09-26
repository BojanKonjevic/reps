
import { test, expect, Page } from '@playwright/test';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const dir = dirname(fileURLToPath(import.meta.url));
function fixture(name: string) {
  return JSON.parse(readFileSync(join(dir, 'fixtures', name + '.json'), 'utf8'));
}
const rich = fixture('rich');
const brk = fixture('break');

type Snap = typeof rich;

async function gotoFixture(page: Page, snapshot: unknown, asOf: string) {
  await page.clock.install({ time: new Date(asOf + 'T12:00:00Z') });
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot) })
  );
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

const bench = rich.lifts.find(l => l.exercise === 'bench')!;
const row = rich.lifts.find(l => l.exercise === 'row')!;
const hold = rich.autoreg.holds[0];
const change = rich.autoreg_changes[0];
const goal = rich.goals[0];

test.describe('Rich snapshot sections', () => {
  test('next session card follows last session through the rotation', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#nextWrap')).toContainText(rich.next_up.day);
    const benchRow = page.locator('#nextCard .nextline', { hasText: 'bench' });
    await expect(benchRow).toContainText('100 x 5');
    await expect(benchRow).toContainText('target 102.5x5');
    await expect(page.locator('#nextCard')).toContainText('never logged');
  });

  test('goal cards show percent to target', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#goalGrid .goalmeta').first()).toContainText(`${goal.percent}% there`);
  });

  test('consistency section renders adherence verdicts', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#adhWrap')).toBeVisible();
    const missed = rich.adherence!.days.filter(d => d.status === 'missed').length;
    await expect(page.locator('#adhCard .dt-missed')).toHaveCount(missed);
    const lastWeek = rich.adherence!.weeks[rich.adherence!.weeks.length - 1];
    await expect(page.locator('#adhCard')).toContainText(
      `${lastWeek.trained}/${lastWeek.expected} sessions`
    );
  });

  test('legend dims deprioritized muscles', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    const prone = rich.muscles.filter(m => m.tier === 'priority').map(m => m.muscle);
    const depr = rich.muscles.filter(m => m.tier === 'deprioritize').map(m => m.muscle);
    for (const m of prone) await expect(page.locator('#legMus a.focus', { hasText: m })).toHaveCount(1);
    for (const m of depr.slice(0, 1))
      await expect(page.locator('#legMus a.dim', { hasText: m })).toHaveCount(1);
  });

  test('break line follows the emitted break fact', async ({ page }) => {
    await gotoFixture(page, brk, brk.as_of);
    await expect(page.locator('#nowLines')).toContainText(
      `Break: ${brk.status.break_days}d since last session`
    );
  });

  test('lift page shows time since last PR, first set is the baseline', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/l/bench');
    await expect(page.locator('#liftSub')).toContainText(`last PR ${bench.days_since_pr}d ago`);
    await expect(page.locator('#liftPRs')).toContainText('+2.9');
    await page.goto('#/l/row');
    const rowPRs = await page.locator('#liftSub').textContent();
    expect(rowPRs).toContain(`last PR ${row.days_since_pr}d ago`);
  });

  test('movements page shows rows, badges and filters', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/lifts');
    await expect(page.locator('#liftsSub')).toContainText(`${rich.lifts.length} movements`);
    const benchCard = page.locator('#liftGrid .liftrow', { hasText: 'bench' });
    await expect(benchCard).toContainText(`${hold.action}, holds until ${hold.hold_until}`);
    await expect(benchCard).toContainText(`adjusted ${change.date}: ${change.evidence}`);
    await expect(benchCard).toContainText('best 100 x 5 (e1RM 116.7)');
    await expect(benchCard).toContainText('hit');
    await expect(benchCard).toContainText('102.5x5');
    await expect(benchCard).toContainText('setup: touch low');
    await page.locator('#liftFacets button', { hasText: 'Autoreg' }).click();
    await expect(page.locator('#liftGrid .liftrow')).toHaveCount(1);
    await page.locator('#liftFacets button', { hasText: 'Autoreg' }).click();
    await expect(page.locator('#liftGrid .liftrow')).toHaveCount(rich.lifts.length);
  });

  test('muscles page shows volume status and grouped badges', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.goto('#/muscles');
    const side = page.locator('#musGrid .musrow', { hasText: 'side delts' });
    await expect(side).toContainText('below MEV');
    await page.locator('#musFacets button', { hasText: 'Below MEV' }).click();
    const below = rich.muscles.filter(m => m.status === 'below_mev').length;
    await expect(page.locator('#musGrid .musrow')).toHaveCount(below);
    await page.locator('#musFacets button', { hasText: 'Below MEV' }).click();
    await page.locator('#musFacets button', { hasText: 'Priority' }).click();
    await expect(page.locator('#musGrid .musrow')).toHaveCount(1);
    await expect(page.locator('#musGrid .musrow').first()).toContainText('chest');
  });

  test('coach notes read the snapshot signals aloud', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#sigWrap')).toBeVisible();
    await expect(page.locator('#sigCard .sigtag').first()).toHaveText(rich.signals[0].severity.toUpperCase());
    await expect(page.locator('#sigCard')).toContainText(rich.signals[0].text.slice(0, 40));
  });
});
