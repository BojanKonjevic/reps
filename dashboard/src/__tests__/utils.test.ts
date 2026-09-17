import { describe, it, expect } from 'vitest';
import { fmtV, fmtD, fmtTick, isDate, niceTicks } from '../utils';

describe('utils', () => {
  describe('fmtV', () => {
    it('formats >=100 as integer', () => {
      expect(fmtV(100)).toBe('100');
      expect(fmtV(150.7)).toBe('151');
    });
    it('formats <100 with one decimal', () => {
      expect(fmtV(99.5)).toBe('99.5');
      expect(fmtV(50)).toBe('50.0');
    });
  });

  describe('fmtD', () => {
    it('formats YYYY-MM-DD as Mon DD', () => {
      expect(fmtD('2026-01-15')).toBe('Jan 15');
      expect(fmtD('2026-12-01')).toBe('Dec 1');
    });
  });

  describe('fmtTick', () => {
    it('formats step >=1 with no decimals', () => {
      expect(fmtTick(100, 10)).toBe('100');
    });
    it('formats small step with appropriate decimals', () => {
      // step 0.5 -> dec = min(2, -floor(log10(0.5)+1e-9)) = min(2, 1) = 1
      expect(fmtTick(1.5, 0.5)).toBe('1.5');
      // step 0.1 -> dec = min(2, 1) = 1? log10(0.1) = -1, floor(-1) = -1, -(-1) = 1, min(2, 1) = 1
      expect(fmtTick(1.5, 0.1)).toBe('1.5');
      // step 0.01 -> dec = min(2, 2) = 2
      expect(fmtTick(1.55, 0.01)).toBe('1.55');
    });
  });

  describe('isDate', () => {
    it('validates correct format', () => {
      expect(isDate('2026-01-15')).toBe(true);
      expect(isDate('2026-12-31')).toBe(true);
    });
    it('rejects invalid format', () => {
      expect(isDate('01-15-2026')).toBe(false);
      expect(isDate('2026/01/15')).toBe(false);
      expect(isDate('jan 15 2026')).toBe(false);
      expect(isDate('')).toBe(false);
    });
  });

  describe('niceTicks', () => {
    it('returns reasonable bounds and step', () => {
      const t = niceTicks(0, 100, 4);
      expect(t.lo).toBeLessThanOrEqual(0);
      expect(t.hi).toBeGreaterThanOrEqual(100);
      expect([1, 2, 2.5, 5, 10, 20, 25, 50]).toContain(t.step);
    });
    it('handles negative range', () => {
      const t = niceTicks(-50, 50, 4);
      expect(t.lo).toBeLessThanOrEqual(-50);
      expect(t.hi).toBeGreaterThanOrEqual(50);
    });
    it('handles tiny range', () => {
      const t = niceTicks(100, 101, 4);
      expect(t.step).toBeGreaterThan(0);
    });
  });
});
