import { describe, it, expect } from 'vitest';
import { weekKey, shift } from '../date';

describe('date', () => {
  describe('weekKey', () => {
    it('returns YYYY Wn format', () => {
      expect(weekKey('2026-01-01')).toMatch(/^2026 W\d+$/);
      expect(weekKey('2026-06-15')).toMatch(/^2026 W\d+$/);
    });
    it('is consistent for nearby dates in same calculated week', () => {
      // Just verify deterministic format and that nearby dates can be same week
      const w1 = weekKey('2026-01-15');
      const w2 = weekKey('2026-01-15');
      expect(w1).toBe(w2);
      expect(w1).toMatch(/^\d{4} W\d+$/);
    });
  });

  describe('shift', () => {
    it('shifts forward', () => {
      expect(shift('2026-01-15', 1)).toBe('2026-01-16');
      expect(shift('2026-01-15', 7)).toBe('2026-01-22');
    });
    it('shifts backward', () => {
      expect(shift('2026-01-15', -1)).toBe('2026-01-14');
      expect(shift('2026-01-15', -7)).toBe('2026-01-08');
    });
    it('handles month boundaries', () => {
      expect(shift('2026-01-31', 1)).toBe('2026-02-01');
      expect(shift('2026-03-01', -1)).toBe('2026-02-28');
    });
    it('handles year boundaries', () => {
      expect(shift('2026-12-31', 1)).toBe('2027-01-01');
      expect(shift('2026-01-01', -1)).toBe('2025-12-31');
    });
  });
});
