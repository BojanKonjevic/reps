import { e1rm } from './utils';
import { weekKey } from './date';

export interface SnapSet {
  id: number;
  workout_id: number;
  exercise: string;
  weight: number;
  reps: number;
  note: string;
  created: string;
  muscles: string;
}

export interface SnapWorkout {
  id: number;
  date: string;
  status: string;
  notes: string;
}

export interface SplitRow {
  day: string;
  slot: number;
  movements: string;
  sets: number;
}

export interface GoalEntry {
  id: number;
  exercise: string;
  target_e1rm: number;
  deadline: string;
  checkpoints?: number[];
  completed?: number;
  actuals?: Array<{ date: string; e1rm: number }>;
  on_track?: boolean;
  slippage?: boolean;
  next_checkpoint?: number | null;
  remaining?: number;
  consecutive_misses?: number;
}

export interface ProgressionEntry {
  verdict: string;
  next: string;
  direction: string;
  workout_id: number;
}

export function splitDayExercises(splitActive: SplitRow[]): Record<string, string[]> {
  const out: Record<string, string[]> = {};
  for (const r of splitActive || []) {
    const moves = (r.movements || '')
      .split('/')
      .map(m => m.trim().toLowerCase())
      .filter(m => m);
    out[r.day] = (out[r.day] || []).concat(moves);
  }
  return out;
}

export function labelSession(
  exercises: string[],
  dayMoves: Record<string, string[]>
): string | null {
  const trained = new Set(exercises.map(e => e.toLowerCase()));
  let best: string | null = null;
  let bestScore = 0;
  for (const [day, moves] of Object.entries(dayMoves)) {
    const score = moves.filter(m => trained.has(m)).length;
    if (score > bestScore) {
      bestScore = score;
      best = day;
    }
  }
  return bestScore > 0 ? best : null;
}

export interface AdherenceDay {
  date: string;
  expected: string;
  trained: string | null;
  status: string;
}

export function missedExpected(
  adherence: { days?: AdherenceDay[] } | null | undefined
): Record<string, string> {
  const out: Record<string, string> = {};
  for (const d of (adherence && adherence.days) || []) {
    if (d.status === 'missed') out[d.date] = d.expected;
  }
  return out;
}

export function nextSlot(
  lastDay: string | null,
  rotation: string[]
): { day: string | null; basis: string } {
  if (!lastDay) return { day: null, basis: 'no history' };
  if (!rotation || !rotation.length) return { day: null, basis: 'rotation unparseable' };
  const idx = rotation.findIndex(d => d.toLowerCase() === lastDay.toLowerCase());
  if (idx < 0) return { day: null, basis: 'last day matches no rotation entry' };
  let j = (idx + 1) % rotation.length;
  let skippedRest = false;
  let scanned = 0;
  while (rotation[j].toLowerCase() === 'rest' && scanned < rotation.length) {
    skippedRest = true;
    j = (j + 1) % rotation.length;
    scanned += 1;
  }
  if (scanned >= rotation.length) return { day: null, basis: 'rotation is all rest' };
  const basis =
    'last trained ' +
    lastDay +
    ', rotation ' +
    lastDay +
    '->' +
    rotation[j] +
    (skippedRest ? ' (rest sits between)' : '');
  return { day: rotation[j], basis };
}

export interface StallPoint {
  ev: number;
  slot?: string | null;
}

export function isStalling(pts: StallPoint[]): boolean {
  // A lift is stalling when its last 3 sessions hold no strict PR (first
  // session is the baseline, ties are not PRs) and either it sits more than
  // 1% under its best or that best is 6+ sessions old (never improved counts).
  // Holding at the top for a few sessions is maintenance, not a stall;
  // declining off it or flatlining for weeks is.
  // Deliberately slot-blind: a PR in any slot is progress the chart can see,
  // so the badge never contradicts the line.
  if (pts.length < 4) return false;
  let best = -Infinity;
  let bestIdx = 0;
  const isPR: boolean[] = [];
  pts.forEach((p, i) => {
    if (i === 0) {
      best = p.ev;
      bestIdx = 0;
      isPR.push(false);
      return;
    }
    if (p.ev > best) {
      best = p.ev;
      bestIdx = i;
      isPR.push(true);
    } else {
      isPR.push(false);
    }
  });
  if (isPR.slice(-3).some(v => v)) return false;
  const last = pts[pts.length - 1].ev;
  if (last < best * 0.99) return true;
  if (pts.length - 1 - bestIdx >= 6) return true;
  return false;
}

export function deloadWatch(pts: Array<{ ev: number }>, pct = 5): boolean {
  if (pts.length < 3) return false;
  const a = pts[pts.length - 3].ev;
  const b = pts[pts.length - 2].ev;
  const c = pts[pts.length - 1].ev;
  if (!(a > 0 && b > 0)) return false;
  return (b - a) / a <= -pct / 100 && (c - b) / b <= -pct / 100;
}

export function parseNextTarget(next: string): { w: number; r: number; ev: number } | null {
  const parts = (next || '').toLowerCase().split('x');
  if (parts.length !== 2) return null;
  const w = parseFloat(parts[0].trim());
  const r = parseInt(parts[1].trim(), 10);
  if (!(w > 0) || !(r > 0)) return null;
  return { w, r, ev: e1rm(w, r) };
}

export interface MuscleLift {
  ex: string;
  sets: number;
  share: number;
}

export interface MusclePage {
  labels: string[];
  counts: number[];
  lifts: MuscleLift[];
  sessions: number;
  total: number;
}

export function musclePageData(W: SnapWorkout[], S: SnapSet[], muscle: string): MusclePage {
  const m = muscle.toLowerCase();
  const wdate: Record<number, string> = {};
  for (const w of W) wdate[w.id] = w.date;
  const dayOf = (s: SnapSet) => wdate[s.workout_id] || (s.created || '').slice(0, 10);
  const mine = S.filter(s =>
    (s.muscles || '')
      .split(',')
      .map(x => x.trim().toLowerCase())
      .filter(x => x)
      .includes(m)
  );
  const byWeek: Record<string, number> = {};
  const dates = new Set<string>();
  const perLift: Record<string, number> = {};
  for (const s of mine) {
    const d = dayOf(s);
    if (!d) continue;
    const k = weekKey(d);
    byWeek[k] = (byWeek[k] || 0) + 1;
    dates.add(d);
    perLift[s.exercise] = (perLift[s.exercise] || 0) + 1;
  }
  const labels = Object.keys(byWeek).sort();
  const counts = labels.map(k => byWeek[k]);
  const total = mine.length;
  const lifts = Object.keys(perLift)
    .map(ex => ({ ex, sets: perLift[ex], share: total ? perLift[ex] / total : 0 }))
    .sort((a, b) => b.sets - a.sets);
  return { labels, counts, lifts, sessions: dates.size, total };
}
