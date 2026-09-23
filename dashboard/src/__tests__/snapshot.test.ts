import { describe, it, expect } from 'vitest';
import { snapshotSchema } from '../schemas/snapshot';

// Minimal e2e-style payload: forward sections absent, like a stale sync.
const MINIMAL = {
  exported: '2026-09-17T12:00:00',
  workouts: [{ id: 1, date: '2026-09-10', status: 'done', notes: 'push day' }],
  sets: [
    {
      id: 1,
      workout_id: 1,
      exercise: 'flat barbell bench press',
      weight: 90,
      reps: 5,
      note: '',
      created: '2026-09-10T18:00:00',
      muscles: 'chest',
    },
  ],
  bodyweight: [{ id: 1, date: '2026-09-13', kg: 84.2, note: 'fasted' }],
};

describe('snapshotSchema', () => {
  it('parses a minimal payload with forward sections defaulted', () => {
    const snap = snapshotSchema.parse(MINIMAL);
    expect(snap.workouts).toHaveLength(1);
    expect(snap.split_active).toEqual([]);
    expect(snap.rotation).toEqual([]);
    expect(snap.constants).toBeUndefined();
    expect(snap.adherence).toBeUndefined();
    expect(snap.autoreg).toBeUndefined();
    expect(snap.volume).toEqual({});
    expect(snap.signals).toBeUndefined();
  });

  it('parses a full payload with typed sections', () => {
    const snap = snapshotSchema.parse({
      ...MINIMAL,
      split_active: [{ day: 'Upper A', slot: 1, movements: 'bench', sets: 5 }],
      rotation: ['Upper A', 'rest'],
      constants: {
        muscles: {
          chest: {
            mev: 8,
            mav: [14, 20],
            mrv: 25,
            freq: [2, 3],
            tier: 'settled',
            source: 'x',
            color: '#ffa726',
          },
        },
        thresholds: { break_days: 4 },
      },
      adherence: {
        anchor: { date: '2026-09-01', index: 0 },
        days: [{ date: '2026-09-10', expected: 'Upper A', trained: 'Upper A', status: 'done' }],
        drift: false,
        drift_days: 0,
        drift_threshold: 3,
      },
      autoreg: { permitted: true, grouped: { chest: ['bench'] }, program_volume: { chest: 8 } },
      volume: { chest: { weekly: [8, 8], mev: 8, status: 'in_range' } },
    });
    expect(snap.split_active[0].day).toBe('Upper A');
    expect(snap.adherence?.days[0].status).toBe('done');
    expect(snap.autoreg?.grouped['chest']).toEqual(['bench']);
    expect(snap.volume['chest'].status).toBe('in_range');
  });

  it('rejects a string weight instead of coercing', () => {
    expect(() =>
      snapshotSchema.parse({
        ...MINIMAL,
        sets: [{ ...MINIMAL.sets[0], weight: 'heavy' }],
      })
    ).toThrow();
  });

  it('rejects a missing export stamp', () => {
    const { exported: _drop, ...rest } = MINIMAL;
    expect(() => snapshotSchema.parse(rest)).toThrow();
  });

  it('rejects an unknown workout status', () => {
    expect(() =>
      snapshotSchema.parse({
        ...MINIMAL,
        workouts: [{ id: 1, date: '2026-09-10', status: 'archived', notes: '' }],
      })
    ).toThrow();
  });

  it('tolerates partial constants from a stale payload', () => {
    const snap = snapshotSchema.parse({
      ...MINIMAL,
      constants: {
        thresholds: { break_days: 2 },
        muscles: { chest: { mev: 8 }, back: { mev: 10 } },
      },
    });
    expect(snap.constants?.muscles['chest']?.mev).toBe(8);
    expect(snap.constants?.thresholds['break_days']).toBe(2);
  });
});
