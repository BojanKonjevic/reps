import { describe, it, expect } from 'vitest';
import { LC, liftColor } from '../charts';

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
