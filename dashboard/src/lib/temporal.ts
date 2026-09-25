// SSOT owner: temporal-context selection over embedded history. Consumers:
// pages and temporal components. Pure selection and formatting of facts the
// backend folded (reps/history.py) and described (reps/snapshot.py): relevance
// filtering, date grouping, reversal lookup, unknown-history messaging,
// before/after rendering, then/now comparison. No domain math, no chain
// folding, no clock reads (dates compare as ISO strings; spans use format.ts).

import type {
  DeloadHistoryPayload,
  GoalHistoryPayload,
  HistoryEvent,
  HistoryState,
  ObservationDef,
  PriorityHistoryPayload,
  ProgramHistoryPayload,
  ProgramSlotSnapshot,
  RotationHistoryPayload,
  RuleHistoryPayload,
  Snapshot,
} from '../generated/snapshot';
import { daysBetween, fmtD, fmtV } from './format';

export type { HistoryEvent, HistoryState };

export function historyOf(snap: Snapshot): HistoryEvent[] {
  return snap.history;
}

export function defOf(
  snap: Snapshot,
  metric: Snapshot['observation_defs'][number]['metric']
): ObservationDef | null {
  return snap.observation_defs.find(d => d.metric === metric) ?? null;
}

export function stateOn(snap: Snapshot, date: string): HistoryState | null {
  return snap.history_states.find(s => s.date === date) ?? null;
}

function liftMuscles(snap: Snapshot, exercise: string): string[] {
  const want = exercise.toLowerCase();
  return snap.lifts.find(l => l.exercise.toLowerCase() === want)?.muscles ?? [];
}

function relevant(
  e: HistoryEvent,
  exercises: string[],
  muscles: string[],
  days: string[]
): boolean {
  const ex = new Set(exercises.map(s => s.toLowerCase()));
  const mu = new Set(muscles.map(s => s.toLowerCase()));
  const dy = new Set(days);
  if (e.domain === 'rotation' || e.domain === 'rule') {
    if (!e.affects_exercises.length && !e.affects_muscles.length && !e.affects_days.length)
      return false;
  }
  return (
    e.affects_exercises.some(s => ex.has(s.toLowerCase())) ||
    e.affects_muscles.some(s => mu.has(s.toLowerCase())) ||
    e.affects_days.some(s => dy.has(s))
  );
}

export function eventsForLift(snap: Snapshot, exercise: string): HistoryEvent[] {
  const muscles = liftMuscles(snap, exercise);
  const days = snap.program.days
    .filter(d => d.slots.some(s => s.moves.some(m => m.toLowerCase() === exercise.toLowerCase())))
    .map(d => d.day);
  return snap.history.filter(
    e =>
      (e.domain === 'goal' && e.subject === exercise.toLowerCase()) ||
      (e.domain === 'priority' && muscles.some(m => e.subject === m.toLowerCase())) ||
      (e.domain !== 'goal' && e.domain !== 'priority' && relevant(e, [exercise], muscles, days))
  );
}

export function eventsForMuscle(snap: Snapshot, muscle: string): HistoryEvent[] {
  const want = muscle.toLowerCase();
  return snap.history.filter(
    e =>
      (e.domain === 'priority' && e.subject === want) ||
      (e.domain !== 'priority' && e.domain !== 'rotation' && relevant(e, [], [want], []))
  );
}

export function eventsForGoal(snap: Snapshot, exercise: string): HistoryEvent[] {
  return snap.history.filter(e => e.domain === 'goal' && e.subject === exercise.toLowerCase());
}

export function scopeForLift(snap: Snapshot, exercise: string): EventScope {
  const muscles = liftMuscles(snap, exercise);
  const days = snap.program.days
    .filter(d => d.slots.some(s => s.moves.some(m => m.toLowerCase() === exercise.toLowerCase())))
    .map(d => d.day);
  return { exercises: [exercise], muscles, days };
}

export function ruleIdOf(event: HistoryEvent): number | null {
  if (event.domain !== 'rule') return null;
  const a = event.after as RuleHistoryPayload;
  const b = event.before as RuleHistoryPayload;
  return a.rule_id ?? b.rule_id ?? null;
}

export function programEvents(snap: Snapshot): HistoryEvent[] {
  return snap.history.filter(e => e.domain !== 'goal' && e.domain !== 'priority');
}

export function nearbyEvents(snap: Snapshot, date: string, spanDays = 7): HistoryEvent[] {
  return snap.history
    .filter(e => Math.abs(daysBetween(date, e.date)) <= spanDays)
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.sequence - b.sequence));
}

export function recentChanges(snap: Snapshot, n = 5): HistoryEvent[] {
  return snap.history.slice().sort(byNewest).slice(0, n);
}

export function byNewest(a: HistoryEvent, b: HistoryEvent): number {
  if (a.date !== b.date) return a.date > b.date ? -1 : 1;
  return b.sequence - a.sequence || b.id - a.id;
}

export interface DateGroup {
  date: string;
  events: HistoryEvent[];
}

export function groupByDate(events: HistoryEvent[]): DateGroup[] {
  const order: string[] = [];
  const byDate = new Map<string, HistoryEvent[]>();
  for (const e of events) {
    if (!byDate.has(e.date)) {
      byDate.set(e.date, []);
      order.push(e.date);
    }
    byDate.get(e.date)!.push(e);
  }
  return order.sort().map(date => ({ date, events: byDate.get(date)! }));
}

export function reversalOf(
  event: HistoryEvent,
  events: HistoryEvent[]
): { reverses: HistoryEvent | null; reversedBy: HistoryEvent | null } {
  const byId = new Map(events.map(e => [e.id, e]));
  return {
    reverses: (event.reverses !== null && event.reverses !== undefined
      ? (byId.get(event.reverses) ?? null)
      : null) as HistoryEvent | null,
    reversedBy: (event.superseded_by !== null && event.superseded_by !== undefined
      ? (byId.get(event.superseded_by) ?? null)
      : null) as HistoryEvent | null,
  };
}

export function historyStart(events: HistoryEvent[]): string | null {
  if (!events.length) return null;
  return events.reduce((a, e) => (e.date < a ? e.date : a), events[0].date);
}

// Earliest relevant event vs earliest training datum: when the chart
// reaches further back than recorded history, say so instead of implying
// the past never changed.
export function coverageNote(relevant: HistoryEvent[], dataStart: string | null): string | null {
  const start = historyStart(relevant);
  if (!start || !dataStart || dataStart >= start) return null;
  return 'History from ' + fmtD(start) + ', earlier changes were not recorded.';
}

function fmtOpt(v: number | string | null | undefined): string {
  if (v === null || v === undefined) return 'unset';
  return typeof v === 'number' ? fmtV(v) : v;
}

function slotLine(s: ProgramSlotSnapshot): string {
  return 'slot ' + s.slot + ': ' + s.movements + ' x' + s.sets;
}

function slotLines(slots: ProgramSlotSnapshot[] | null | undefined): string[] {
  if (!slots || !slots.length) return ['no slots recorded'];
  return slots
    .slice()
    .sort((a, b) => a.slot - b.slot)
    .map(slotLine);
}

// Narrow the unmarked before/after union by domain through the generated
// payload types: a backend field rename fails the build here instead of
// rendering silently wrong.
export function envelopeLines(domain: string, payload: HistoryEvent['before']): string[] {
  if (domain === 'program') {
    return slotLines((payload as ProgramHistoryPayload).slots ?? null);
  }
  if (domain === 'priority') {
    const p = payload as PriorityHistoryPayload;
    return ['tier: ' + fmtOpt(p.tier), 'since: ' + fmtOpt(p.since), 'until: ' + fmtOpt(p.until)];
  }
  if (domain === 'goal') {
    const p = payload as GoalHistoryPayload;
    return [
      'target: ' + fmtOpt(p.target_e1rm) + ' e1RM',
      'by: ' + fmtOpt(p.deadline),
      'status: ' + fmtOpt(p.status),
      Array.isArray(p.checkpoints)
        ? p.checkpoints.length + ' checkpoints'
        : 'no trajectory recorded',
    ];
  }
  if (domain === 'deload') {
    const p = payload as DeloadHistoryPayload;
    return [
      (p.scope ?? 'unset') + ' ' + (p.subject ?? 'unset'),
      (p.active ? 'active' : 'not active') + ' (' + p.action + ')',
    ];
  }
  if (domain === 'rule') {
    const p = payload as RuleHistoryPayload;
    return [p.text ?? 'no text', 'status: ' + fmtOpt(p.status), 'expiry: ' + fmtOpt(p.expiry)];
  }
  if (domain === 'rotation') {
    const p = payload as RotationHistoryPayload;
    if (p.anchor_date !== undefined || p.position !== undefined) {
      return ['anchor: ' + fmtOpt(p.anchor_date), 'position: ' + fmtOpt(p.position)];
    }
    if (!Array.isArray(p.rotation)) return ['no rotation recorded'];
    return ['order: ' + rotOrder(p.rotation)];
  }
  return ['change recorded'];
}

export function rotOrder(rot: Array<string | null>): string {
  return rot.map(d => (d === null ? 'rest' : d)).join(' / ');
}

const DOMAIN_LABELS: Record<string, string> = {
  program: 'Program',
  goal: 'Goal',
  priority: 'Priority',
  rotation: 'Rotation',
  rule: 'Rule',
  deload: 'Deload',
};

export function domainLabel(domain: string): string {
  return DOMAIN_LABELS[domain] ?? domain;
}

// Historical goal targets stay visible: one line per changed field,
// before on the left, so rewrites never rewrite history. Adds and drops
// read from the populated envelope instead of diffing against nothing.
export function trajectoryLines(event: HistoryEvent): string[] {
  if (event.domain !== 'goal') return [];
  const b = event.before as GoalHistoryPayload;
  const a = event.after as GoalHistoryPayload;
  const f = (d: string | null | undefined) => (d ? fmtD(d) : 'unset');
  if (a.action === 'add') {
    return ['target ' + fmtOpt(a.target_e1rm) + ' e1RM', 'by ' + f(a.deadline)];
  }
  if (a.action === 'drop') {
    return ['was ' + fmtOpt(b.target_e1rm) + ' e1RM', 'was by ' + f(b.deadline)];
  }
  const out: string[] = [];
  if (b.target_e1rm !== a.target_e1rm) {
    out.push(fmtOpt(b.target_e1rm) + ' → ' + fmtOpt(a.target_e1rm) + ' e1RM');
  }
  if (b.deadline !== a.deadline) {
    out.push('by ' + f(b.deadline) + ' → by ' + f(a.deadline));
  }
  if (b.status !== a.status) {
    out.push(fmtOpt(b.status) + ' → ' + fmtOpt(a.status));
  }
  return out;
}

export function filterHistory(
  events: HistoryEvent[],
  domains: Set<string>,
  from: string,
  to: string
): HistoryEvent[] {
  return events
    .filter(e => !domains.size || domains.has(e.domain))
    .filter(e => !from || e.date >= from)
    .filter(e => !to || e.date <= to)
    .slice()
    .sort(byNewest);
}

export interface SlotDiff {
  slot: number;
  then: string;
  now: string;
  changed: boolean;
}

export function currentSlotLine(slot: number, moves: string[], sets: number): string {
  return 'slot ' + slot + ': ' + moves.join(' / ') + ' x' + sets;
}

// Week-bucket index of a date among emitted week starts (selection over the
// backend's buckets, never re-bucketing): the last start at or before date.
export function weekIndexOf(weekStarts: string[], date: string): number {
  let idx = -1;
  for (let i = 0; i < weekStarts.length; i += 1) if (weekStarts[i] <= date) idx = i;
  return idx;
}

export function diffSlots(
  then: ProgramSlotSnapshot[],
  now: Array<{ slot: number; moves: string[]; sets: number }>
): SlotDiff[] {
  const nowBy = new Map(now.map(s => [s.slot, s]));
  const thenBy = new Map(then.map(s => [s.slot, s]));
  const slots = Array.from(new Set([...thenBy.keys(), ...nowBy.keys()])).sort((a, b) => a - b);
  return slots.map(slot => {
    const t = thenBy.get(slot);
    const n = nowBy.get(slot);
    const thenLine = t ? slotLine(t) : 'slot added since';
    const nowLine = n ? currentSlotLine(n.slot, n.moves, n.sets) : 'slot removed since';
    return { slot, then: thenLine, now: nowLine, changed: thenLine !== nowLine };
  });
}

export interface EventScope {
  exercises: string[];
  muscles: string[];
  days: string[];
}

export function scopeOf(event: HistoryEvent): EventScope {
  return {
    exercises: event.affects_exercises,
    muscles: event.affects_muscles,
    days: event.affects_days,
  };
}
