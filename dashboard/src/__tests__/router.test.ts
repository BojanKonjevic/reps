import { describe, it, expect } from 'vitest';
import { parseHash } from '../router';

describe('parseHash', () => {
  it('routes the dashboard root', () => {
    expect(parseHash('')).toEqual({ name: 'dash' });
    expect(parseHash('#/')).toEqual({ name: 'dash' });
    expect(parseHash('#/unknown')).toEqual({ name: 'dash' });
  });

  it('routes dated sessions only for real dates', () => {
    expect(parseHash('#/s/2026-09-10')).toEqual({ name: 'sess', date: '2026-09-10' });
    expect(parseHash('#/s/not-a-date')).toEqual({ name: 'dash' });
  });

  it('routes lifts, muscles, and list pages', () => {
    expect(parseHash('#/l/bench')).toEqual({ name: 'lift', exercise: 'bench' });
    expect(parseHash('#/l/flat%20bench')).toEqual({ name: 'lift', exercise: 'flat bench' });
    expect(parseHash('#/m/chest')).toEqual({ name: 'muscle', muscle: 'chest' });
    expect(parseHash('#/program')).toEqual({ name: 'prog' });
    expect(parseHash('#/lifts')).toEqual({ name: 'lifts' });
    expect(parseHash('#/muscles')).toEqual({ name: 'muscles' });
    expect(parseHash('#/history')).toEqual({ name: 'hist' });
  });
});
