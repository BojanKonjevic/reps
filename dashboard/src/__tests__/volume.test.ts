import { describe, it, expect } from 'vitest';

describe('volume aggregation logic', () => {
  const blank = () => ({
    chest: 0,
    back: 0,
    shoulders: 0,
    biceps: 0,
    triceps: 0,
    quads: 0,
    hamstrings: 0,
    glutes: 0,
    abs: 0,
    forearms: 0,
  });

  it('aggregates stored muscles per set', () => {
    const weeks: Record<string, Record<string, number>> = {};
    const k = '2026 W1';
    weeks[k] = blank();
    const muscles = 'chest,triceps';
    muscles.split(',').forEach(g => {
      if (g in weeks[k]) weeks[k][g] += 1;
    });
    expect(weeks[k].chest).toBe(1);
    expect(weeks[k].triceps).toBe(1);
    expect(weeks[k].back).toBe(0);
  });

  it('ignores unknown muscle groups', () => {
    const weeks: Record<string, Record<string, number>> = {};
    const k = '2026 W1';
    weeks[k] = blank();
    const muscles = 'chest,neck';
    muscles.split(',').forEach(g => {
      if (g in weeks[k]) weeks[k][g] += 1;
    });
    expect(weeks[k].chest).toBe(1);
    // neck not in GROUPS, ignored
  });

  it('sums multiple sets correctly', () => {
    const weeks: Record<string, Record<string, number>> = {};
    const k = '2026 W1';
    weeks[k] = blank();
    ['chest', 'chest,triceps', 'chest'].forEach(m =>
      m.split(',').forEach(g => {
        if (g in weeks[k]) weeks[k][g] += 1;
      })
    );
    expect(weeks[k].chest).toBe(3);
    expect(weeks[k].triceps).toBe(1);
  });
});
