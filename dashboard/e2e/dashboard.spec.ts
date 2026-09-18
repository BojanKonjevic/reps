import { test, expect, Page } from '@playwright/test';

// Frozen clock so the calendar/today highlight is identical on every run.
const BASE_TIME = new Date('2026-09-17T12:00:00Z');

const MOCK_SNAPSHOT = {
  exported: '2026-09-17T12:00:00',
  workouts: [
    { id: 1, date: '2026-09-10', status: 'done', notes: 'push day' },
    { id: 2, date: '2026-09-14', status: 'done', notes: 'pull day' },
  ],
  sets: [
    { id: 1, workout_id: 1, exercise: 'flat barbell bench press', weight: 90, reps: 5, note: '', created: '2026-09-10T18:00:00', muscles: 'chest' },
    { id: 2, workout_id: 1, exercise: 'flat barbell bench press', weight: 90, reps: 4, note: '', created: '2026-09-10T18:05:00', muscles: 'chest' },
    { id: 3, workout_id: 1, exercise: 'overhead press', weight: 42.5, reps: 7, note: '', created: '2026-09-10T18:15:00', muscles: 'shoulders' },
    { id: 4, workout_id: 2, exercise: 'flat barbell bench press', weight: 92.5, reps: 5, note: '', created: '2026-09-14T18:00:00', muscles: 'chest' },
    { id: 5, workout_id: 2, exercise: 'lat pulldown', weight: 70, reps: 8, note: '', created: '2026-09-14T18:10:00', muscles: 'back' },
  ],
  bodyweight: [
    { id: 1, date: '2026-09-13', kg: 84.2, note: 'fasted' },
    { id: 2, date: '2026-09-14', kg: 84.0, note: 'fasted' },
  ],
};

async function gotoDashboard(page: Page) {
  await page.clock.install({ time: BASE_TIME });
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(MOCK_SNAPSHOT) })
  );
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

test.describe('Dashboard', () => {
  test('loads and shows dashboard title', async ({ page }) => {
    await gotoDashboard(page);
    await expect(page.locator('#viewDash h1')).toContainText('Training dashboard');
  });

  test('renders sessions, calendar and best sets', async ({ page }) => {
    await gotoDashboard(page);
    await expect(page.locator('#sub')).toContainText('2 sessions');
    // Both trained days are links in the calendar.
    await expect(page.locator('.cal a.cd.t')).toHaveCount(2);
    // Best-sets table lists the bench PR (92.5x5 beats 90x5).
    await expect(page.locator('#prs')).toContainText('flat barbell bench press');
    await expect(page.locator('#prs')).toContainText('92.5 x 5');
  });

  test('dashboard visual regression - desktop', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium', 'desktop snapshot only on chromium');
    await gotoDashboard(page);
    await expect(page.locator('#sub')).toContainText('2 sessions');
    // Ratio-based: macOS (Core Text) and Linux (FreeType) rasterize the same
    // font bytes slightly differently, so pixel-perfect cross-OS matching is
    // impossible. 5% still catches any real layout breakage by an order of
    // magnitude (a missing section alone shifts >10%).
    await expect(page).toHaveScreenshot('dashboard-desktop.png', {
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    });
  });

  test('dashboard visual regression - mobile', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'mobile', 'mobile snapshot only on mobile');
    await gotoDashboard(page);
    await expect(page.locator('#sub')).toContainText('2 sessions');
    await expect(page).toHaveScreenshot('dashboard-mobile.png', {
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    });
  });
});
