import { describe, it, expect, beforeEach } from 'vitest';
import {
  rankLifts,
  statusLines,
  bestSetRows,
  dayAvgs,
  adherenceWeeksView,
  liftNames,
  SMALL_SHARE,
} from '../lib/dashboard';
import { ui, defaultHide, pruneHidden, toggleHidden, showAllLifts } from '../lib/filters.svelte';
import { vocabOf } from '../lib/vocab.svelte';
import { sessionSpans } from '../lib/select';
import { showTip, hideTip } from '../tip';
import type { Snapshot } from '../generated/snapshot';
import rich from './fixtures/rich.json';

const snap = rich as unknown as Snapshot;

describe('dashboard view selectors', () => {
  it('rankLifts follows rank_default order', () => {
    const ranked = rankLifts(snap);
    expect(ranked.length).toBe(snap.lifts.length);
    const byRank = snap.lifts.slice().sort((a, b) => a.rank_default - b.rank_default);
    expect(ranked[0]).toBe(byRank[0].exercise);
  });

  it('statusLines renders open/break/deload segments without math', () => {
    const lines = statusLines(snap);
    expect(Array.isArray(lines)).toBe(true);
    for (const line of lines) for (const seg of line) expect(typeof seg.t).toBe('string');
  });

  it('bestSetRows skips lifts without a best and formats detail', () => {
    const rows = bestSetRows(snap);
    for (const r of rows) expect(r.detail).toContain('e1RM');
    expect(rows.length).toBe(snap.lifts.filter(l => l.best).length);
  });

  it('dayAvgs averages emitted minutes per slot label', () => {
    const spans = sessionSpans(snap.sessions);
    const avgs = dayAvgs(spans);
    for (const a of avgs) {
      const group = spans.filter(s => s.day === a.day);
      expect(a.n).toBe(group.length);
      expect(a.avg).toBeCloseTo(group.reduce((x, s) => x + s.minutes, 0) / group.length, 1);
    }
  });

  it('adherenceWeeksView caps at the last 8 weeks', () => {
    expect(adherenceWeeksView(snap).length).toBeLessThanOrEqual(8);
  });

  it('liftNames sorts alphabetically', () => {
    const names = liftNames(snap);
    expect(names).toEqual(names.slice().sort());
  });

  it('SMALL_SHARE is a fraction between 0 and 1', () => {
    expect(SMALL_SHARE).toBeGreaterThan(0);
    expect(SMALL_SHARE).toBeLessThan(1);
  });
});

describe('filter UI state', () => {
  beforeEach(() => {
    showAllLifts();
    ui.hiddenTouched = false;
  });

  it('defaultHide hides past the snapshot cutoff on first visit only', () => {
    const names = ['a', 'b', 'c', 'd'];
    defaultHide(names, 2);
    expect(Array.from(ui.hidden)).toEqual(['c', 'd']);
    ui.hidden.clear();
    ui.hiddenTouched = true;
    defaultHide(names, 2);
    expect(ui.hidden.size).toBe(0);
  });

  it('pruneHidden drops saved names missing from the snapshot', () => {
    ui.hidden.add('ghost');
    pruneHidden(['bench']);
    expect(ui.hidden.has('ghost')).toBe(false);
  });

  it('toggleHidden flips membership and marks touched', () => {
    toggleHidden('bench');
    expect(ui.hidden.has('bench')).toBe(true);
    expect(ui.hiddenTouched).toBe(true);
    toggleHidden('bench');
    expect(ui.hidden.has('bench')).toBe(false);
  });
});

describe('vocabOf fallbacks', () => {
  it('reads colors and groups from snapshot constants', () => {
    const v = vocabOf(snap);
    expect(v.groups.length).toBeGreaterThan(0);
    expect(Object.keys(v.colors).length).toBeGreaterThan(0);
  });

  it('bands fall back to mev 0 and null ranges for unknown muscles', () => {
    const v = vocabOf(snap);
    expect(v.bands('not-a-muscle')).toEqual({ mev: 0, mav: null, mrv: null });
  });
});

describe('tip live region', () => {
  it('showTip creates an aria-live status node and hideTip dismisses it', () => {
    showTip('bench', [[null, '100 x 5']], 10, 10);
    const el = document.querySelector('.tip');
    expect(el).not.toBeNull();
    expect(el!.getAttribute('aria-live')).toBe('polite');
    expect(el!.textContent).toContain('bench');
    hideTip();
    expect((el as HTMLElement).style.display).toBe('none');
  });
});
