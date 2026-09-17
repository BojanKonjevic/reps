import { describe, it, expect } from 'vitest';
import { computePRs } from '../prs';

describe('computePRs', () => {
  it('detects first set as baseline (not PR)', () => {
    const W = [{ id: 1, date: '2026-01-01' }];
    const S = [
      {
        id: 1,
        workout_id: 1,
        exercise: 'bench',
        weight: 100,
        reps: 5,
        created: '2026-01-01T10:00:00',
      },
    ];
    const pr = computePRs(W, S);
    expect(pr.prIds.size).toBe(0);
    expect(pr.prDates.size).toBe(0);
  });

  it('detects new e1RM as PR', () => {
    const W = [
      { id: 1, date: '2026-01-01' },
      { id: 2, date: '2026-01-08' },
    ];
    const S = [
      {
        id: 1,
        workout_id: 1,
        exercise: 'bench',
        weight: 100,
        reps: 5,
        created: '2026-01-01T10:00:00',
      },
      {
        id: 2,
        workout_id: 2,
        exercise: 'bench',
        weight: 105,
        reps: 5,
        created: '2026-01-08T10:00:00',
      },
    ];
    const pr = computePRs(W, S);
    expect(pr.prIds.has(2)).toBe(true);
    expect(pr.prDates.has('2026-01-08')).toBe(true);
  });

  it('ignores same weight', () => {
    const W = [
      { id: 1, date: '2026-01-01' },
      { id: 2, date: '2026-01-08' },
    ];
    const S = [
      {
        id: 1,
        workout_id: 1,
        exercise: 'bench',
        weight: 100,
        reps: 5,
        created: '2026-01-01T10:00:00',
      },
      {
        id: 2,
        workout_id: 2,
        exercise: 'bench',
        weight: 100,
        reps: 5,
        created: '2026-01-08T10:00:00',
      },
    ];
    const pr = computePRs(W, S);
    expect(pr.prIds.size).toBe(0);
  });

  it('handles multiple exercises independently', () => {
    const W = [
      { id: 1, date: '2026-01-01' },
      { id: 2, date: '2026-01-08' },
    ];
    const S = [
      {
        id: 1,
        workout_id: 1,
        exercise: 'bench',
        weight: 100,
        reps: 5,
        created: '2026-01-01T10:00:00',
      },
      {
        id: 2,
        workout_id: 1,
        exercise: 'squat',
        weight: 150,
        reps: 5,
        created: '2026-01-01T10:00:00',
      },
      {
        id: 3,
        workout_id: 2,
        exercise: 'bench',
        weight: 105,
        reps: 5,
        created: '2026-01-08T10:00:00',
      },
      {
        id: 4,
        workout_id: 2,
        exercise: 'squat',
        weight: 150,
        reps: 5,
        created: '2026-01-08T10:00:00',
      },
    ];
    const pr = computePRs(W, S);
    expect(pr.prIds.has(3)).toBe(true); // bench PR
    expect(pr.prIds.has(4)).toBe(false); // squat no PR
  });

  it('ignores zero weight sets', () => {
    const W = [{ id: 1, date: '2026-01-01' }];
    const S = [
      {
        id: 1,
        workout_id: 1,
        exercise: 'bench',
        weight: 0,
        reps: 5,
        created: '2026-01-01T10:00:00',
      },
    ];
    const pr = computePRs(W, S);
    expect(pr.prIds.size).toBe(0);
  });
});
