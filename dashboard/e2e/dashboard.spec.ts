
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

// Viewer clock follows the fixture: relative values render against as_of,
// so freezing the clock there keeps calendar highlights deterministic.
async function gotoFixture(page: Page, snapshot: unknown, asOf: string) {
  await page.clock.install({ time: new Date(asOf + 'T12:00:00Z') });
  await page.route('**/snapshot', r =>
    r.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(snapshot) })
  );
  await page.goto('/');
  await page.waitForLoadState('networkidle');
}

const sessionsOf = (s: Snap) => {
  const n = s.sessions.filter(x => x.status !== 'rest').length;
  return `${n} session${n === 1 ? '' : 's'}`;
};

test.describe('Dashboard', () => {
  test('loads and shows dashboard title', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#viewDash h1')).toContainText('Training dashboard');
  });

  test('renders sessions, calendar and best sets', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#sub')).toContainText(`${sessionsOf(rich)}`);
    const lastMonth = rich.calendar[rich.calendar.length - 1].date.slice(0, 7);
    const trained = rich.calendar.filter(d => d.kind === 'trained' && d.date.startsWith(lastMonth));
    await expect(page.locator('.cal a.cd.t')).toHaveCount(trained.length);
    await expect(page.locator('#prs')).toContainText('bench');
    await expect(page.locator('#prs')).toContainText('100 x 5');
  });

  test('session length chart renders below the calendar', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#sessLenWrap')).toBeVisible();
    await expect(page.locator('#chSessLen')).toBeVisible();
  });

  test('command palette jumps between pages', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.keyboard.press('Control+k');
    await expect(page.locator('.pal-panel')).toBeVisible();
    await page.locator('.pal-panel input').fill('muscles');
    await page.keyboard.press('Enter');
    await expect(page.locator('#viewMuscles')).toBeVisible();
    await expect(page.locator('.pal-panel')).toBeHidden();
    await page.keyboard.press('Control+k');
    await expect(page.locator('.pal-panel')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('.pal-panel')).toBeHidden();
  });

  test('palette arrows cycle and esc closes without input focus', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    await page.keyboard.press('Control+k');
    await expect(page.locator('.pal-panel')).toBeVisible();
    const rows = page.locator('.pal-panel button');
    for (let i = 0; i < 4; i += 1) await page.keyboard.press('ArrowDown');
    await expect(rows.first()).toHaveClass(/pal-active/);
    await page.keyboard.press('ArrowUp');
    await expect(rows.last()).toHaveClass(/pal-active/);
    await page.evaluate(() => (document.activeElement as HTMLElement | null)?.blur?.());
    await page.keyboard.press('Escape');
    await expect(page.locator('.pal-panel')).toBeHidden();
  });

  test('going back returns to the saved scroll position', async ({ page }) => {
    await gotoFixture(page, rich, rich.as_of);
    const link = page.locator('#trendGrid .mini a').first();
    await link.scrollIntoViewIfNeeded();
    await page.waitForTimeout(100);
    const y0 = await page.evaluate(() => window.scrollY);
    await link.click();
    await expect(page.locator('#viewLift')).toBeVisible();
    await page.goBack();
    await expect(page.locator('#viewDash')).toBeVisible();
    await page.waitForTimeout(200);
    const y = await page.evaluate(() => window.scrollY);
    expect(Math.abs(y - y0)).toBeLessThan(60);
  });

  test('mini charts repaint at full size after returning from a lift page', async ({ page }) => {    await gotoFixture(page, rich, rich.as_of);
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
    await gotoFixture(page, brk, brk.as_of);
    await expect(page.locator('#sub')).toContainText(`${sessionsOf(brk)}`);
    await expect(page.locator('.cal a.cd.r')).toHaveCount(1);
    await page.locator('.cal a.cd.r').click();
    await expect(page.locator('#viewSession')).toBeVisible();
    await expect(page.locator('#sessNotes')).toContainText('rest day');
    await expect(page.locator('#sessNotes')).toContainText('sore legs');
  });

  test('dashboard visual regression - desktop', async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== 'chromium', 'desktop snapshot only on chromium');
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#sub')).toContainText(`${sessionsOf(rich)}`);
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
    await gotoFixture(page, rich, rich.as_of);
    await expect(page.locator('#sub')).toContainText(`${sessionsOf(rich)}`);
    await expect(page).toHaveScreenshot('dashboard-mobile.png', {
      maxDiffPixelRatio: 0.05,
      threshold: 0.2,
    });
  });
});
