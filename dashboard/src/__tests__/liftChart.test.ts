import { describe, it, expect } from 'vitest';
import { sessionIndexOf } from '../liftChart';

describe('sessionIndexOf', () => {
  const dates = ['2026-09-20', '2026-09-22', '2026-09-26'];
  it('lands exactly on session dates', () => {
    expect(sessionIndexOf(dates, '2026-09-20')).toBe(0);
    expect(sessionIndexOf(dates, '2026-09-22')).toBe(1);
    expect(sessionIndexOf(dates, '2026-09-26')).toBe(2);
  });
  it('clamps outside the span', () => {
    expect(sessionIndexOf(dates, '2026-09-18')).toBe(0);
    expect(sessionIndexOf(dates, '2026-09-30')).toBe(2);
  });
  it('interpolates between sessions', () => {
    expect(sessionIndexOf(dates, '2026-09-21')).toBe(0.5);
    expect(sessionIndexOf(dates, '2026-09-24')).toBe(1.5);
  });
  it('handles duplicate session dates and empty input', () => {
    expect(sessionIndexOf(['2026-09-22', '2026-09-22'], '2026-09-22')).toBe(0);
    expect(sessionIndexOf([], '2026-09-22')).toBe(0);
  });
});
