// Temporal context: relevance, grouping, formatting, reversal, unknown
// history, provenance, and then/now comparison. The rich fixture below was
// built by tests/scenarios.py through the real backend (scripts/gen.py).
import { describe, it, expect } from 'vitest';
import { markDates } from '../liftChart';
import {
  byNewest,
  chartMarks,
  coverageNote,
  defOf,
  diffSlots,
  domainLabel,
  envelopeLines,
  eventsForGoal,
  eventsForLift,
  eventsForMuscle,
  filterHistory,
  groupByDate,
  nearbyEvents,
  rangeBounds,
  recentChanges,
  reversalOf,
  rotOrder,
  ruleIdOf,
  scopeForLift,
  scopeOf,
  selectStateForDate,
  trajectoryLines,
  weekIndexOf,
  weekMarks,
} from '../lib/temporal';
import type { HistoryEvent } from '../generated/snapshot';
import type { HistoryState } from '../generated/historyStates';
import rich from './fixtures/rich.json';
import richStates from './fixtures/rich.states.json';

const snap = rich as unknown as Parameters<typeof eventsForLift>[0];

describe('event relevance', () => {
  it('keeps lift-relevant changes off unrelated lifts', () => {
    const bench = eventsForLift(snap, 'bench').map(e => e.title);
    expect(bench).toContain('Upper A changed');
    expect(bench).toContain('Bench goal set');
    expect(bench).toContain('Chest priority changed');
    expect(bench).not.toContain('Upper B changed');
    expect(bench.every(e => e !== 'Rotation changed')).toBe(true);
    expect(bench.every(e => e !== 'Schedule re-anchored')).toBe(true);
  });

  it('keeps muscle-relevant changes off unrelated muscles', () => {
    const chest = eventsForMuscle(snap, 'chest').map(e => e.title);
    expect(chest).toContain('Chest priority changed');
    expect(chest).toContain('Upper A changed');
    expect(chest).not.toContain('Upper B changed');
    const back = eventsForMuscle(snap, 'back').map(e => e.title);
    expect(back).toContain('Upper B changed');
    expect(back).not.toContain('Upper A changed');
  });

  it('scopes goal charts to their own exercise', () => {
    expect(eventsForGoal(snap, 'bench').map(e => e.title)).toEqual(['Bench goal set']);
    expect(eventsForGoal(snap, 'row')).toEqual([]);
  });
});

describe('grouping and recency', () => {
  it('collapses same-date events into one group', () => {
    const groups = groupByDate(eventsForLift(snap, 'bench'));
    expect(groups).toHaveLength(1);
    expect(groups[0].events.length).toBeGreaterThan(1);
  });

  it('lists newest changes first, capped', () => {
    const top = recentChanges(snap, 5);
    expect(top).toHaveLength(5);
    for (let i = 1; i < top.length; i += 1) expect(top[i - 1].date >= top[i].date).toBe(true);
  });

  it('finds nearby changes in a date window', () => {
    const near = nearbyEvents(snap, '2026-09-24', 7);
    expect(near.length).toBeGreaterThan(0);
    expect(nearbyEvents(snap, '2020-01-01', 7)).toEqual([]);
  });
});

describe('before/after rendering', () => {
  it('renders program slots without raw JSON', () => {
    const e = eventsForLift(snap, 'bench').find(x => x.title === 'Upper A changed')!;
    const after = envelopeLines(e.domain, e.after);
    expect(after.join('\n')).toContain('sets');
    expect(after.join('\n')).not.toContain('{');
  });

  it('renders goal targets and trajectory counts', () => {
    const e = eventsForGoal(snap, 'bench')[0];
    expect(envelopeLines(e.domain, e.after).join(' | ')).toContain('e1RM');
    expect(trajectoryLines(e).join(' | ')).toContain('target');
  });

  it('keeps historical targets visible after a rewrite', () => {
    const b = { target_e1rm: 140, deadline: '2026-12-01', status: 'active' };
    const a = { target_e1rm: 135, deadline: '2026-12-01', status: 'active', action: 'rewrite' };
    const e = { domain: 'goal', before: b, after: a } as unknown as HistoryEvent;
    expect(trajectoryLines(e)).toEqual(['140 → 135 e1RM']);
    const drop = {
      domain: 'goal',
      before: b,
      after: { ...a, action: 'drop' },
    } as unknown as HistoryEvent;
    expect(trajectoryLines(drop)).toEqual(['was 140 e1RM', 'was by Dec 1']);
  });

  it('reads rule ids and scopes off events', () => {
    const rule = snap.history.find(e => e.domain === 'rule')!;
    expect(ruleIdOf(rule)).toBeGreaterThan(0);
    expect(ruleIdOf(snap.history.find(e => e.domain === 'goal')!)).toBeNull();
    expect(scopeOf(rule)).toEqual({ exercises: [], muscles: [], days: [] });
    expect(scopeForLift(snap, 'bench')).toEqual({
      exercises: ['bench'],
      muscles: ['chest'],
      days: ['Upper A'],
    });
  });
});

describe('reversal and supersession', () => {
  it('links an inverse to its original both ways', () => {
    const [a, b] = snap.history;
    const orig = { ...a, superseded_by: 9999 };
    const rev = { ...b, id: 9999, reverses: a.id };
    expect(reversalOf(rev, [orig, rev]).reverses?.id).toBe(a.id);
    expect(reversalOf(orig, [orig, rev]).reversedBy?.id).toBe(9999);
    expect(reversalOf(a, snap.history).reverses).toBeNull();
    expect(reversalOf(a, snap.history).reversedBy).toBeNull();
  });
});

describe('unknown history', () => {
  it('bounds the supported as-of range by recorded history and today', () => {
    expect(rangeBounds(snap)).toEqual({ min: '2026-09-24', max: snap.as_of });
  });

  it('warns when training predates recorded history', () => {
    const events = eventsForLift(snap, 'bench');
    expect(coverageNote(events, '2026-09-04')).toContain('earlier changes were not recorded');
    expect(coverageNote(events, '2026-09-24')).toBeNull();
    expect(coverageNote([], '2026-09-04')).toBeNull();
  });

  it('selects folded states by date, never inventing them', () => {
    const states = (richStates as { states: HistoryState[] }).states;
    expect(selectStateForDate(states, '2026-09-24')?.program.length).toBeGreaterThan(0);
    expect(selectStateForDate(states, '2026-09-30')?.date).toBe('2026-09-24');
    expect(selectStateForDate(states, '2020-01-01')).toBeNull();
    expect(selectStateForDate([], '2026-09-24')).toBeNull();
  });
});

describe('provenance', () => {
  it('serves backend-owned definitions per metric', () => {
    const def = defOf(snap, 'lift_trend')!;
    expect(def.definition).toContain('e1RM');
    expect(def.sources).toContain('sets');
    expect(defOf(snap, 'muscle_volume')?.sources).toContain('set_muscle');
    // Unknown metrics cannot typecheck: probe with a cast, expect null.
    expect(defOf(snap, 'nope' as 'lift_trend')).toBeNull();
  });

  it('labels every history domain', () => {
    expect(['program', 'goal', 'priority', 'rotation', 'rule', 'deload'].map(domainLabel)).toEqual([
      'Program',
      'Goal',
      'Priority',
      'Rotation',
      'Rule',
      'Deload',
    ]);
  });
});

describe('comparison and chart mapping', () => {
  it('diffs then/now slots per slot number', () => {
    const diffs = diffSlots(
      [{ slot: 1, movements: 'squat', sets: 3 }],
      [{ slot: 1, moves: ['squat'], sets: 2 }]
    );
    expect(diffs).toEqual([
      { slot: 1, then: 'squat · 3 sets', now: 'squat · 2 sets', changed: true },
    ]);
    expect(
      diffSlots(
        [{ slot: 1, movements: 'squat', sets: 2 }],
        [{ slot: 1, moves: ['squat'], sets: 2 }]
      )[0].changed
    ).toBe(false);
  });

  it('tells added slots from removed ones', () => {
    const diffs = diffSlots(
      [{ slot: 1, movements: 'squat', sets: 3 }],
      [
        { slot: 1, moves: ['squat'], sets: 3 },
        { slot: 2, moves: ['lunge'], sets: 2 },
      ]
    );
    expect(diffs[1]).toEqual({
      slot: 2,
      then: 'slot added since',
      now: 'lunge · 2 sets',
      changed: true,
    });
    const gone = diffSlots(
      [
        { slot: 1, movements: 'squat', sets: 3 },
        { slot: 2, movements: 'lunge', sets: 2 },
      ],
      [{ slot: 1, moves: ['squat'], sets: 3 }]
    );
    expect(gone[1].now).toBe('slot removed since');
    expect(rotOrder(['Upper A', null])).toBe('Upper A / rest');
  });

  it('orders newest first down to sequence and id', () => {
    const mk = (date: string, sequence: number, id: number) =>
      ({ date, sequence, id }) as HistoryEvent;
    const rows = [mk('2026-09-20', 0, 3), mk('2026-09-24', 0, 1), mk('2026-09-24', 1, 2)];
    expect(rows.sort(byNewest).map(r => r.id)).toEqual([2, 1, 3]);
  });

  it('maps event dates onto week buckets and lift spans', () => {
    const starts = snap.volume_history.week_starts;
    expect(weekIndexOf(starts, '2026-09-24')).toBe(starts.length - 1);
    expect(weekIndexOf(starts, '2020-01-01')).toBe(-1);
    const bench = snap.lifts.find(l => l.exercise === 'bench')!;
    const pts = bench.sessions.map(s => ({ date: s.date, w: 0, r: 0, ev: 0, pr: false }));
    const last = pts[pts.length - 1].date;
    const found = markDates(pts, chartMarks(groupByDate(eventsForLift(snap, 'bench'))));
    expect(found.every(m => m.date >= pts[0].date && m.date <= last)).toBe(true);
    expect(markDates(pts, [{ date: last, titles: [] }]).map(m => m.date)).toEqual([last]);
    const weeks = weekMarks(groupByDate(eventsForMuscle(snap, 'chest')), starts);
    expect(weeks.every(m => m.week !== undefined && m.week >= 0)).toBe(true);
  });

  it('filters history by domain and range, newest first', () => {
    const goals = filterHistory(snap.history, new Set(['goal']), '', '');
    expect(goals.map(e => e.title)).toEqual(['Bench goal set']);
    expect(filterHistory(snap.history, new Set(), '2026-09-24', '2026-09-24')).toHaveLength(
      snap.history.length
    );
    expect(filterHistory(snap.history, new Set(), '2020-01-01', '2020-01-02')).toEqual([]);
  });
});
