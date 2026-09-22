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
    bench: { verdict: 'hit', next: '95x5', direction: 'up', workout_id: 3, note: 'paused reps' },
  },
  mapping: [
    { exercise: 'bench', muscles: 'chest', is_bodyweight_only: 0 },
    { exercise: 'squat', muscles: 'quads', is_bodyweight_only: 0 },
  ],
  movement_notes: [{ exercise: 'bench', note: 'touch low', created: '2026-09-14T19:00:00' }],
  autoreg: {
    permitted: true,
    holds: [
      { id: 1, day: 'Upper A', movements: 'flat barbell bench press', action: 'trim', set_on: '2026-09-15', hold_until: '2026-09-23', reason: 'two misses' },
    ],
    miss_streaks: [],
    drop_watch: [],
    grouped: { chest: ['flat barbell bench press'] },
    program_volume: {},
  },
  autoreg_changes: [
    { id: 1, date: '2026-09-15', action: 'trim', day: 'Upper A', slot: 1, before_movements: 'bench', before_sets: 3, after_movements: 'bench', after_sets: 2, evidence: 'two misses', reverted_on: null },
  ],
  volume: {
    chest: { weekly: [0, 0, 0, 0, 0, 0, 3, 2], mev: 8, mav: [14, 20], mrv: 25, freq: [2, 3], status: 'below_mev' },
    back: { weekly: [3, 3, 3, 3, 3, 3, 3, 3], mev: 10, mav: [14, 22], mrv: 28, freq: [2, 3], status: 'in_range' },
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
  signals: [
    { severity: 'high', text: 'chest: 0 sets in 7 of last 8 weeks (MEV 8)' },
    { severity: 'info', text: 'deloading lift bench' },
  ],
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

  test('legend dims deprioritized muscles', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#legMus a.dim').first()).toContainText('back');
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

  test('movements page shows cards, badges and filters', async ({ page }) => {
    await gotoRich(page);
    await page.goto('#/lifts');
    await expect(page.locator('#liftsSub')).toContainText('2 movements');
    const bench = page.locator('#liftGrid .card', { hasText: 'flat barbell bench press' });
    await expect(bench).toContainText('trim, holds until 2026-09-23');
    await expect(bench).toContainText('adjusted 2026-09-15: two misses');
    await expect(bench).toContainText('grouped fatigue: chest');
    await expect(bench).toContainText('best 92.5 x 5 (e1RM 108)');
    await expect(bench).toContainText('hit ↑ 95x5 · paused reps');
    await expect(bench).toContainText('hit → 95x5 up · paused reps');
    await expect(bench).toContainText('setup: touch low');
    await page.locator('#liftFacets button', { hasText: 'Autoreg' }).click();
    await expect(page.locator('#liftGrid .card')).toHaveCount(1);
    await page.locator('#liftFacets button', { hasText: 'Autoreg' }).click();
    await expect(page.locator('#liftGrid .card')).toHaveCount(2);
  });

  test('muscles page shows volume status and grouped badges', async ({ page }) => {
    await gotoRich(page);
    await page.goto('#/muscles');
    const chest = page.locator('#musGrid .card', { hasText: 'chest' });
    await expect(chest).toContainText('below MEV');
    await expect(chest).toContainText('grouped fatigue: flat barbell bench press');
    await expect(page.locator('#musGrid')).toContainText('in range');
    await page.locator('#musFacets button', { hasText: 'Below MEV' }).click();
    await expect(page.locator('#musGrid .card')).toHaveCount(1);
    await page.locator('#musFacets button', { hasText: 'Below MEV' }).click();
    await page.locator('#musFacets button', { hasText: 'Priority' }).click();
    await expect(page.locator('#musGrid .card')).toHaveCount(1);
    await expect(page.locator('#musGrid .card').first()).toContainText('chest');
  });

  test('coach notes read the snapshot signals aloud', async ({ page }) => {
    await gotoRich(page);
    await expect(page.locator('#sigWrap')).toBeVisible();
    await expect(page.locator('#sigCard .sigtag').first()).toHaveText('HIGH');
    await expect(page.locator('#sigCard')).toContainText('chest: 0 sets in 7 of last 8 weeks');
  });
});
