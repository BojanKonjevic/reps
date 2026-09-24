import { describe, it, expect } from 'vitest';
import { LC, liftColor } from '../charts';
import { visibleStart, labelIndices } from '../stackedChart';

describe('liftColor', () => {
  it('is stable per exercise name', () => {
    expect(liftColor('bench press')).toBe(liftColor('bench press'));
    expect(liftColor('Bench Press')).toBe(liftColor('bench press'));
  });
  it('stays inside the palette', () => {
    for (const ex of ['bench', 'squat', 'deadlift', 'ohp', 'row', 'dip', 'curl']) {
      expect(LC).toContain(liftColor(ex));
    }
  });
  it('spreads across the palette instead of colliding', () => {
    const lifts = ['bench', 'squat', 'deadlift', 'ohp', 'row', 'dip', 'curl', 'pullup'];
    const cols = new Set(lifts.map(liftColor));
    expect(cols.size).toBeGreaterThan(1);
  });
});

describe('stacked volume trimming', () => {
  const groups = ['chest', 'back'];
  it('trims leading empty weeks, keeps the current week', () => {
    const weeks: Array<Record<string, number>> = [{}, {}, { chest: 71 }, { chest: 5 }];
    expect(visibleStart(weeks, groups)).toBe(2);
  });
  it('single nonzero last week starts at the end', () => {
    const weeks: Array<Record<string, number>> = [{}, {}, { chest: 71 }];
    expect(visibleStart(weeks, groups)).toBe(2);
  });
  it('all empty keeps one week instead of dividing by zero', () => {
    expect(visibleStart([{}, {}], groups)).toBe(1);
  });
});

describe('stacked volume labels', () => {
  it('shows every label when few weeks are visible', () => {
    expect(labelIndices(1)).toEqual([0]);
    expect(labelIndices(4)).toEqual([0, 1, 2, 3]);
  });
  it('never forces a colliding last label', () => {
    expect(labelIndices(8)).toEqual([0, 2, 4, 6]);
    expect(labelIndices(6)).toEqual([0, 2, 4]);
  });
});
