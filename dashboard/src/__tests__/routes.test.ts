import { describe, it, expect } from 'vitest';
import { href, parse, isDate } from '../routes';

describe('routes', () => {
  it('round-trips every builder through the parser', () => {
    expect(parse(href.lift('flat bench'))).toEqual({ name: 'lift', exercise: 'flat bench' });
    expect(parse(href.session('2026-09-10'))).toEqual({ name: 'session', date: '2026-09-10' });
    expect(parse(href.muscle('front delts'))).toEqual({ name: 'muscle', muscle: 'front delts' });
    expect(parse(href.program())).toEqual({ name: 'program' });
    expect(parse(href.lifts())).toEqual({ name: 'lifts' });
    expect(parse(href.muscles())).toEqual({ name: 'muscles' });
    expect(parse(href.history())).toEqual({ name: 'history' });
    expect(parse(href.dash())).toEqual({ name: 'dash' });
  });

  it('falls back to dash for unknown or undated routes', () => {
    expect(parse('#/unknown')).toEqual({ name: 'dash' });
    expect(parse('')).toEqual({ name: 'dash' });
    expect(parse('#/s/not-a-date')).toEqual({ name: 'dash' });
  });

  it('validates ISO dates in one place', () => {
    expect(isDate('2026-09-10')).toBe(true);
    expect(isDate('2026-9-10')).toBe(false);
    expect(isDate('')).toBe(false);
  });
});
