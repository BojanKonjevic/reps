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
    { id: 3, workout_id: 1, exercise: 'overhead press', weight: 42.5, reps: 7, note: '', created: '2026-09-10T18:15:00', muscles: 'front delts' },
    { id: 4, workout_id: 2, exercise: 'flat barbell bench press', weight: 92.5, reps: 5, note: '', created: '2026-09-14T18:00:00', muscles: 'chest' },
    { id: 5, workout_id: 2, exercise: 'straight bar pulldown', weight: 70, reps: 8, note: '', created: '2026-09-14T18:10:00', muscles: 'back' },
  ],
  bodyweight: [
    { id: 1, date: '2026-09-13', kg: 84.2, note: 'fasted' },
    { id: 2, date: '2026-09-14', kg: 84.0, note: 'fasted' },
  ],
};

async function gotoDashboard(page: Page, snapshot: unknown = MOCK_SNAPSHOT) {
  await page.clock.install({ time: BASE_TIME });
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot) })
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

  test('mini charts repaint at full size after returning from a lift page', async ({ page }) => {
    await gotoDashboard(page);
    await page.locator('#trendGrid .mini a').first().click();
    await expect(page.locator('#viewLift')).toBeVisible();
    // Resize while the dash is hidden: the debounced render must not bake a
    // zero-size bitmap into the minis (fit clamps hidden canvases to 50px,
    // which CSS then stretches into smears).
    const size = page.viewportSize()!;
    await page.setViewportSize({ width: size.width - 100, height: size.height });
    await page.waitForTimeout(500);
    await page.goBack();
    await expect(page.locator('#viewDash')).toBeVisible();
    await page.waitForFunction(() => {
      const cv = document.querySelector('#trendGrid .mini canvas');
      return cv instanceof HTMLCanvasElement && cv.width > 100;
    });
  });

  test('rest days show distinctly and are not counted as sessions', async ({ page }) => {
    await gotoDashboard(page, {
      ...MOCK_SNAPSHOT,
      workouts: [
        ...MOCK_SNAPSHOT.workouts,
        { id: 3, date: '2026-09-12', status: 'rest', notes: 'sore legs' },
      ],
    });
    // Rest is not a session.
    await expect(page.locator('#sub')).toContainText('2 sessions');
    await expect(page.locator('.cal a.cd.t')).toHaveCount(2);
    // ...but it is tracked, clearly different from absence.
    await expect(page.locator('.cal a.cd.r')).toHaveCount(1);
    await page.locator('.cal a.cd.r').click();
    await expect(page.locator('#viewSession')).toBeVisible();
    await expect(page.locator('#sessNotes')).toContainText('rest day');
    await expect(page.locator('#sessNotes')).toContainText('sore legs');
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
