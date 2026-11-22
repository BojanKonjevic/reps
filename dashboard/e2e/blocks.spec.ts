import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';
import type { Snapshot } from '../src/generated/snapshot';

const blocks: Snapshot = JSON.parse(
  readFileSync(new URL('./fixtures/blocks.json', import.meta.url), 'utf8')
);

test('browse completed and current blocks without resetting all-time records', async ({ page }) => {
  await page.clock.install({ time: new Date(blocks.as_of + 'T12:00:00Z') });
  await page.route('**/snapshot', route => route.fulfill({ json: blocks }));
  await page.goto('/');
  const picker = page.getByRole('button', { name: /^Training history:/ });
  await expect(picker).toHaveAccessibleName('Training history: All time');
  const [titleBox, pickerBox] = await Promise.all([
    page.getByRole('heading', { name: 'Overview' }).boundingBox(),
    picker.boundingBox(),
  ]);
  expect(pickerBox!.x).toBeGreaterThan(titleBox!.x);
  expect(Math.abs(pickerBox!.y - titleBox!.y)).toBeLessThan(8);
  expect(pickerBox!.height).toBeGreaterThanOrEqual(40);
  await expect(page.getByText('Dashed lines mark block dates')).toHaveCount(0);
  await expect(page.locator('.cal .block-edge')).not.toHaveCount(0);

  await picker.click();
  await expect(page.getByRole('menuitemradio', { name: 'All time' })).toBeFocused();
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('menuitemradio', { name: /^Block 2/ })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(picker).toBeFocused();
  await expect(page.getByRole('menu', { name: 'Training history' })).toHaveCount(0);
  await picker.click();
  await page.getByRole('menuitemradio', { name: /^Block 1/ }).click();
  const note = page.getByRole('heading', { name: 'Final coach note' });
  const history = page.getByRole('heading', { name: 'What changed' });
  const review = page.locator('details.block-signals');
  await expect(review).toHaveJSProperty('open', false);
  await review.locator('summary').click();
  await expect(review).toHaveJSProperty('open', true);
  await expect(review).toContainText('No signals in this block');
  await expect(page.locator('#sigWrap')).toHaveCount(0);
  await expect(note).toBeVisible();
  const weight = page.getByRole('group', { name: 'Block bodyweight' });
  await expect(weight).toContainText('79.0 kg');
  await expect(weight).toContainText('83.0 kg');
  await expect(weight).not.toContainText(/Sep|weigh-ins/);
  await expect(page.getByRole('heading', { name: 'Progress', exact: true })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Next block', exact: true })).toBeVisible();
  await expect(page.getByText('Bench moved up.', { exact: true })).toBeVisible();
  await expect(history).toBeVisible();
  const [headingBox, noteBox, historyBox] = await Promise.all([
    page.getByRole('heading', { name: 'Overview' }).boundingBox(),
    note.boundingBox(),
    history.boundingBox(),
  ]);
  expect(noteBox!.y).toBeGreaterThan(headingBox!.y);
  if (page.viewportSize()!.width > 900) {
    expect(noteBox!.x).toBeLessThan(historyBox!.x);
    expect(Math.abs(noteBox!.y - historyBox!.y)).toBeLessThan(5);
  } else {
    expect(noteBox!.y).toBeLessThan(historyBox!.y);
  }
  await expect(page.locator('#nextWrap')).toHaveCount(0);
  await expect(page.locator('#blockResults')).toContainText('96.0');
  await page.locator('#blockResults').getByRole('link', { name: 'bench' }).click();
  await expect(picker).toHaveAccessibleName('Training history: Block 1');
  await expect(page.locator('#viewLift')).toContainText('Block best 96.0 e1RM');
  await expect(page.locator('#viewLift')).toContainText('all-time best 102 e1RM');

  await page.goto('/#/');
  await picker.click();
  await expect(page.getByRole('menuitemradio', { name: /^Block 1/ })).toHaveAttribute(
    'aria-checked',
    'true'
  );
  await page.getByRole('menuitemradio', { name: /^Block 2/ }).click();
  await expect(page.getByRole('heading', { name: 'Changes from previous block' })).toBeVisible();
  await expect(page.getByText('Partial window at the block boundary')).toBeVisible();
  await page.getByRole('link', { name: /bench.*4 sets/ }).click();
  await expect(page.locator('#histList .evbtn[aria-pressed="true"]')).toHaveCount(1);
});
