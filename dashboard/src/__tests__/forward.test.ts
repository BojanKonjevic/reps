import { describe, it, expect } from 'vitest';
import {
  labelSession,
  nextSlot,
  isStalling,
  deloadWatch,
  parseNextTarget,
  musclePageData,
} from '../forward';

describe('slot labeling and rotation', () => {
  const days = { U1: ['bench press', 'row'], L1: ['squat', 'leg curl'] };
  it('labels a session by best overlap', () => {
    expect(labelSession(['bench press', 'row', 'curl'], days)).toBe('U1');
  });
  it('returns null with no overlap', () => {
    expect(labelSession(['curl'], days)).toBeNull();
  });
  it('steps to the next rotation day and skips rest', () => {
    expect(nextSlot('U1', ['U1', 'L1', 'U2', 'rest']).day).toBe('L1');
    expect(nextSlot('U2', ['U1', 'L1', 'U2', 'rest', 'U3']).day).toBe('U3');
  });
  it('handles no history', () => {
    expect(nextSlot(null, ['U1', 'L1']).day).toBeNull();
  });
  it('handles an all-rest rotation without hanging', () => {
    expect(nextSlot('rest', ['rest']).day).toBeNull();
  });
});

describe('stall and deload signals', () => {
  it('flags a run sitting below best with no recent PR', () => {
    expect(isStalling([{ ev: 100 }, { ev: 102 }, { ev: 101 }, { ev: 100 }, { ev: 99 }])).toBe(true);
  });
  it('does not flag ties held at the top', () => {
    expect(isStalling([{ ev: 100 }, { ev: 102 }, { ev: 102 }, { ev: 102 }])).toBe(false);
  });
  it('flags a flatline that never improved', () => {
    const flat = [100, 100, 100, 100, 100, 100, 100].map(ev => ({ ev }));
    expect(isStalling(flat)).toBe(true);
  });
  it('does not flag a recent PR', () => {
    expect(isStalling([{ ev: 100 }, { ev: 90 }, { ev: 95 }, { ev: 101 }])).toBe(false);
  });
  it('needs history before judging', () => {
    expect(isStalling([{ ev: 100 }, { ev: 99 }, { ev: 98 }])).toBe(false);
  });
  it('flags two consecutive 5pct drops', () => {
    expect(deloadWatch([{ ev: 100 }, { ev: 94 }, { ev: 88 }])).toBe(true);
    expect(deloadWatch([{ ev: 100 }, { ev: 99 }, { ev: 101 }])).toBe(false);
  });
});

describe('next target parsing', () => {
  it('parses WxR targets into e1rm', () => {
    const t = parseNextTarget('80x5');
    expect(t && t.w).toBe(80);
    expect(t && t.r).toBe(5);
  });
  it('rejects free text', () => {
    expect(parseNextTarget('test')).toBeNull();
  });
});

describe('muscle page data', () => {
  const W = [
    { id: 1, date: '2026-09-10', status: 'done', notes: '' },
    { id: 2, date: '2026-09-14', status: 'done', notes: '' },
  ];
  const S = [
    {
      id: 1,
      workout_id: 1,
      exercise: 'bench',
      weight: 80,
      reps: 5,
      note: '',
      created: '2026-09-10T18:00:00',
      muscles: 'chest,front delts',
    },
    {
      id: 2,
      workout_id: 1,
      exercise: 'curl',
      weight: 30,
      reps: 8,
      note: '',
      created: '2026-09-10T18:10:00',
      muscles: 'biceps',
    },
    {
      id: 3,
      workout_id: 2,
      exercise: 'bench',
      weight: 82.5,
      reps: 5,
      note: '',
      created: '2026-09-14T18:00:00',
      muscles: 'chest,front delts',
    },
  ];
  it('credits compounds to every mapped muscle', () => {
    const chest = musclePageData(W, S, 'chest');
    expect(chest.total).toBe(2);
    expect(chest.sessions).toBe(2);
    expect(chest.lifts[0].ex).toBe('bench');
    const front = musclePageData(W, S, 'front delts');
    expect(front.total).toBe(2);
  });
  it('isolates single-muscle moves', () => {
    const bi = musclePageData(W, S, 'biceps');
    expect(bi.total).toBe(1);
    expect(bi.lifts[0].share).toBe(1);
  });
  it('returns empty for untrained muscles', () => {
    const q = musclePageData(W, S, 'quads');
    expect(q.total).toBe(0);
    expect(q.labels).toEqual([]);
  });
});
