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

export function stallSessions(pts: Array<{ ev: number }>): number {
  if (pts.length < 2) return 0;
  const best = Math.max(...pts.map(p => p.ev));
  let n = 0;
  for (let i = pts.length - 1; i >= 0; i -= 1) {
    if (pts[i].ev >= best) break;
    n += 1;
  }
  return n;
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
