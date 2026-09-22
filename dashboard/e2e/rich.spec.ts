import { test, expect, Page } from '@playwright/test';

// Frozen clock so the calendar/today highlight is identical on every run.
const BASE_TIME = new Date('2026-09-17T12:00:00Z');

const RICH_SNAPSHOT = {
  exported: '2026-09-17T12:00:00',
  workouts: [
    { id: 1, date: '2026-09-07', status: 'done', notes: '' },
    { id: 2, date: '2026-09-10', status: 'done', notes: '' },
    { id: 3, date: '2026-09-14', status: 'done', notes: '' },
  ],
  sets: [
    { id: 1, workout_id: 1, exercise: 'squat', weight: 100, reps: 5, note: '', created: '2026-09-07T18:00:00', muscles: 'quads' },
    { id: 2, workout_id: 2, exercise: 'bench', weight: 90, reps: 5, note: '', created: '2026-09-10T18:00:00', muscles: 'chest' },
    { id: 3, workout_id: 3, exercise: 'bench', weight: 92.5, reps: 5, note: '', created: '2026-09-14T18:00:00', muscles: 'chest' },
  ],
  bodyweight: [
    { id: 1, date: '2026-09-13', kg: 84.2, note: '' },
    { id: 2, date: '2026-09-14', kg: 84.0, note: '' },
  ],
  split_active: [
    { day: 'Upper A', slot: 1, movements: 'bench', sets: 3 },
    { day: 'Lower A', slot: 1, movements: 'squat', sets: 3 },
  ],
  rotation: ['Upper A', 'Lower A', 'rest'],
  constants: {
    thresholds: { break_days: 2 },
    muscles: {
      chest: { mev: 8 },
      back: { mev: 10 },
    },
  },
  progression: {
    bench: { verdict: 'hit', next: '95x5', direction: 'up', workout_id: 3 },
  },
  goals: [
    {
      id: 1,
      exercise: 'bench',
      target_e1rm: 130,
      target_desc: '',
      deadline: '2026-12-01',
      checkpoints: [100, 110, 120, 130],
      actuals: [
        { date: '2026-09-10', e1rm: 105 },
        { date: '2026-09-14', e1rm: 108 },
      ],
      next_checkpoint: 120,
      on_track: true,
    },
  ],
  priority: {
    chest: { tier: 'priority', since: '2026-09-01', until: null },
    back: { tier: 'deprioritize', since: '2026-09-01', until: null },
  },
  adherence: {
    anchor: { date: '2026-09-10', index: 0 },
    days: [
      { date: '2026-09-10', expected: 'Upper A', trained: 'Upper A', status: 'done' },
      { date: '2026-09-11', expected: 'Lower A', trained: null, status: 'missed' },
      { date: '2026-09-12', expected: 'rest', trained: null, status: 'rest_ok' },
    ],
  },
};

async function gotoRich(page: Page) {
  await page.clock.install({ time: BASE_TIME });
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(RICH_SNAPSHOT) })
  );
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

test.describe('Rich snapshot sections', () => {
  test('next session card follows last session through the rotation', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#nextCard h3')).toContainText('Next up: Lower A');
    const squat = page.locator('#nextCard .nextrow', { hasText: 'squat' });
    await expect(squat).toContainText('last 100 x 5');
    await expect(squat).toContainText('no target yet');
  });

  test('same-slot section lists runs per day', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#slotGrid .slotcard')).toHaveCount(2);
    await expect(page.locator('#slotGrid')).toContainText('bench 92.5x5');
  });

  test('goal cards show percent to target', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#goalGrid .goalmeta').first()).toContainText('27% there');
  });

  test('consistency section renders adherence verdicts', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#adhWrap')).toBeVisible();
    await expect(page.locator('#adhCard .dt-missed')).toHaveCount(1);
    await expect(page.locator('#adhCard')).toContainText('1/2 sessions');
  });

  test('legend dims deprioritized muscles and marks MEV attainment', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#legMus a.dim').first()).toContainText('back');
    await expect(page.locator('#legMus .chip .meta').first()).toContainText('/');
  });

  test('break line follows snapshot break_days, not a hardcoded 5', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#nowLines')).toContainText('Break: 3d since last session');
  });

  test('lift page shows time since last PR, first set is the baseline', async ({ page }) => {
    await gotoRich(page);
    await page.goto('#/l/bench');
    await expect(page.locator('#liftPRs')).toContainText('last PR 3d ago');
    await page.goto('#/l/squat');
    await expect(page.locator('#liftPRs')).toContainText('no PR yet');
  });
});
