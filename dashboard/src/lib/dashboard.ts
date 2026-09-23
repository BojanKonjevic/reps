import {
  adherenceWeeks,
  type AdherenceWeek,
  deloadWatch,
  isStalling,
  labelSession,
  missedExpected,
  nextSlot,
  splitDayExercises,
} from '../forward';
import { computePRs, type PRData } from '../prs';
import { e1rm, fmtD, fmtV } from '../utils';
import type { Snapshot } from '../schemas/snapshot';

// Pure derived data for pages. This module owns every computation the old
// imperative controller did inline: pages render its outputs as markup and
// hand its point arrays to canvas components. No DOM in here.

export interface TrendModel {
  days: string[];
  series: Array<Array<number | null>>;
  top: string[];
  meta: Array<Array<{ w: number; r: number } | null>>;
}

export function workoutDateOf(snap: Snapshot): Record<number, string> {
  const m: Record<number, string> = {};
  for (const w of snap.workouts) m[w.id] = w.date;
  return m;
}

export function sessionDateOfSet(snap: Snapshot, workoutId: number, created: string): string {
  return workoutDateOf(snap)[workoutId] || created.slice(0, 10);
}

export function subLine(snap: Snapshot): string {
  const sessions = snap.workouts.filter(w => w.status !== 'rest');
  if (sessions.length) return sessions.length + (sessions.length === 1 ? ' session' : ' sessions');
  if (snap.workouts.length) return 'no sessions yet, ' + snap.workouts.length + ' rest days logged';
  return 'no sync yet, log your first session';
}

export function goalExerciseSet(snap: Snapshot): Set<string> {
  return new Set(snap.goals.map(g => String(g['exercise'] || '').toLowerCase()));
}

export function musclesOf(snap: Snapshot, exercise: string): string[] {
  const hit = snap.mapping.filter(
    r => String(r['exercise'] || '').toLowerCase() === exercise.toLowerCase()
  );
  if (!hit.length) return [];
  return String(hit[0]['muscles'] || '')
    .split(',')
    .map(x => x.trim())
    .filter(x => x);
}

export function notesOf(snap: Snapshot, exercise: string): string[] {
  return snap.movement_notes
    .filter(r => String(r['exercise'] || '').toLowerCase() === exercise.toLowerCase())
    .map(r => String(r['note'] || ''))
    .filter(n => n);
}

export function prioMuscles(snap: Snapshot): Set<string> {
  return new Set(
    Object.keys(snap.priority)
      .filter(m => {
        const t = snap.priority[m] as string | { tier?: string } | undefined;
        return (typeof t === 'string' ? t : t?.tier) === 'priority';
      })
      .map(m => m.toLowerCase())
  );
}

export function deprioMuscles(snap: Snapshot): Set<string> {
  return new Set(
    Object.keys(snap.priority)
      .filter(m => {
        const t = snap.priority[m] as string | { tier?: string } | undefined;
        return (typeof t === 'string' ? t : t?.tier) === 'deprioritize';
      })
      .map(m => m.toLowerCase())
  );
}

export function rankLifts(snap: Snapshot): string[] {
  const goalEx = goalExerciseSet(snap);
  const prio = prioMuscles(snap);
  const rank = (ex: string) => {
    if (goalEx.has(ex.toLowerCase())) return 0;
    if (musclesOf(snap, ex).some(m => prio.has(m.toLowerCase()))) return 1;
    return 2;
  };
  const counts: Record<string, number> = {};
  for (const s of snap.sets) if (s.weight > 0) counts[s.exercise] = (counts[s.exercise] || 0) + 1;
  return Object.entries(counts)
    .sort((a, b) => rank(a[0]) - rank(b[0]) || b[1] - a[1])
    .map(e => e[0]);
}

export function computeTrend(snap: Snapshot, top: string[]): TrendModel {
  const wdate = workoutDateOf(snap);
  const byDate: Record<string, typeof snap.sets> = {};
  for (const s of snap.sets) {
    if (s.weight <= 0) continue;
    const d = wdate[s.workout_id] || s.created.slice(0, 10);
    (byDate[d] = byDate[d] || []).push(s);
  }
  const days = Object.keys(byDate).sort();
  const series = top.map(t =>
    days.map(d => {
      const sets = byDate[d].filter(s => s.exercise === t);
      if (!sets.length) return null;
      return Math.max(...sets.map(s => e1rm(s.weight, s.reps)));
    })
  );
  const meta = top.map(t =>
    days.map(d => {
      const sets = byDate[d].filter(s => s.exercise === t);
      if (!sets.length) return null;
      const best = sets.slice().sort((a, b) => e1rm(b.weight, b.reps) - e1rm(a.weight, a.reps))[0];
      return { w: best.weight, r: best.reps };
    })
  );
  return { days, series, top, meta };
}

export function slotOfDate(snap: Snapshot): Record<string, string> {
  const wdate = workoutDateOf(snap);
  const moves = splitDayExercises(
    snap.split_active.map(r => ({ day: r.day, slot: r.slot, movements: r.movements, sets: r.sets }))
  );
  const sessEx: Record<string, string[]> = {};
  for (const s of snap.sets) {
    const d = wdate[s.workout_id] || s.created.slice(0, 10);
    (sessEx[d] = sessEx[d] || []).push(s.exercise);
  }
  const out: Record<string, string> = {};
  for (const d of Object.keys(sessEx)) {
    const lab = labelSession(sessEx[d], moves);
    if (lab) out[d] = lab;
  }
  return out;
}

export interface NoteLine {
  date: string;
  text: string;
  hot: boolean;
}

export function recentNotes(snap: Snapshot): NoteLine[] {
  const wdate = workoutDateOf(snap);
  const noted: Record<string, string> = {};
  for (const w of snap.workouts) if (w.notes) noted[w.date] = w.notes;
  for (const s of snap.sets) {
    if (s.note && s.note.trim()) {
      const d = wdate[s.workout_id] || s.created.slice(0, 10);
      noted[d] = (noted[d] ? noted[d] + ' / ' : '') + s.exercise + ': ' + s.note.trim();
    }
  }
  return Object.keys(noted)
    .sort()
    .slice(-6)
    .map(d => {
      const low = noted[d].toLowerCase();
      const hot =
        low.includes('pain') ||
        low.includes('sleep') ||
        low.includes('sore') ||
        low.includes('injury');
      return { date: d, text: fmtD(d) + ': ' + noted[d], hot };
    });
}

export interface PrRow {
  lift: string;
  detail: string;
  date: string;
}

export function bestSetRows(snap: Snapshot): PrRow[] {
  const wdate = workoutDateOf(snap);
  const prs: Record<string, { s: (typeof snap.sets)[number]; ev: number }> = {};
  for (const s of snap.sets) {
    const ev = e1rm(s.weight, s.reps);
    if (!prs[s.exercise] || ev > prs[s.exercise].ev) prs[s.exercise] = { s, ev };
  }
  return Object.keys(prs)
    .sort()
    .map(k => {
      const p = prs[k];
      return {
        lift: k,
        detail: p.s.weight + ' x ' + p.s.reps + ' (e1RM ' + p.ev.toFixed(1) + ')',
        date: fmtD(wdate[p.s.workout_id] || ''),
      };
    });
}

export function breakGap(snap: Snapshot): number {
  const t = (snap.constants?.thresholds || {}) as Record<string, number>;
  return (t['break_days'] || 4) + 1;
}

export interface NowSeg {
  t: string;
  b: boolean;
}

export function nowLines(snap: Snapshot): NowSeg[][] {
  const out: NowSeg[][] = [];
  const line = (...segs: Array<[string, boolean]>) => out.push(segs.map(([t, b]) => ({ t, b })));
  const todayS = new Date().toISOString().slice(0, 10);
  const todayRows = snap.workouts.filter(w => w.date === todayS);
  if (todayRows.some(w => w.status === 'open')) line(['Workout open today.', true]);
  else if (todayRows.some(w => w.status === 'rest')) line(['Rest day today.', false]);
  const doneDates = snap.workouts
    .filter(w => w.status === 'done' && snap.sets.some(s => s.workout_id === w.id))
    .map(w => w.date)
    .sort();
  if (doneDates.length) {
    const gap = Math.round(
      (new Date(todayS + 'T12:00:00').getTime() -
        new Date(doneDates[doneDates.length - 1] + 'T12:00:00').getTime()) /
        86400000
    );
    if (gap >= breakGap(snap))
      line(['Break:', true], [' ' + gap + 'd since last session, no PR attempts.', false]);
  }
  for (const d of snap.deload)
    line(['Deloading', true], [' ' + String(d['subject'] || '') + '.', false]);
  for (const m of Object.keys(snap.priority)) {
    const t = snap.priority[m] as string | { tier?: string } | undefined;
    const tier = typeof t === 'string' ? t : t?.tier;
    if (tier && tier !== 'maintain') line(['Focus:', true], [' ' + m + '.', false]);
  }
  snap.flags.slice(0, 3).forEach(f => {
    line(
      ['Watch:', true],
      [' ' + String(f['subject'] || '') + ', ' + String(f['reason'] || ''), false]
    );
  });
  if (snap.flags.length > 3) line(['+' + (snap.flags.length - 3) + ' more flags in chat.', false]);
  return out;
}

export interface NextRow {
  movement: string;
  detail: string;
}

export interface NextUp {
  day: string;
  rows: NextRow[];
  basis: string;
}

export function nextUp(snap: Snapshot): NextUp | { empty: string } {
  const wdate = workoutDateOf(snap);
  const done = snap.workouts
    .filter(w => w.status === 'done' && snap.sets.some(s => s.workout_id === w.id))
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.id - b.id));
  const moves = splitDayExercises(
    snap.split_active.map(r => ({ day: r.day, slot: r.slot, movements: r.movements, sets: r.sets }))
  );
  const last = done.length ? done[done.length - 1] : null;
  const lastEx = last ? snap.sets.filter(s => s.workout_id === last.id).map(s => s.exercise) : [];
  const lastDay = last ? labelSession(lastEx, moves) : null;
  const nxt = nextSlot(lastDay, snap.rotation || []);
  if (!last || !lastDay || !nxt.day || !(moves[nxt.day] || []).length) {
    return {
      empty: !Object.keys(moves).length
        ? 'no program synced yet, split show in chat is the source'
        : 'log a session and the next slot appears here',
    };
  }
  const prog = snap.progression as Record<string, { next?: string; direction?: string }>;
  const rows = (moves[nxt.day] || []).map(m => {
    const hist = snap.sets.filter(s => (s.exercise || '').toLowerCase() === m.toLowerCase());
    const lastDate = hist.length
      ? hist
          .map(s => wdate[s.workout_id] || s.created.slice(0, 10))
          .sort()
          .pop()!
      : null;
    const daySets = lastDate
      ? hist.filter(s => (wdate[s.workout_id] || s.created.slice(0, 10)) === lastDate)
      : [];
    const top = daySets.length
      ? daySets.slice().sort((a, b) => e1rm(b.weight, b.reps) - e1rm(a.weight, a.reps))[0]
      : null;
    const p = prog[m.toLowerCase()];
    return {
      movement: m,
      detail:
        (top ? 'last ' + top.weight + ' x ' + top.reps + ' · ' + fmtD(lastDate!) : 'never logged') +
        (p ? ' → target ' + p.next + ' ' + p.direction : ' · no target yet'),
    };
  });
  return {
    day: nxt.day,
    rows,
    basis: nxt.basis + '. Confirm or override in chat before training.',
  };
}

export function adherenceWeeksView(snap: Snapshot): AdherenceWeek[] {
  const days = (snap.adherence?.days || []).map(d => ({
    date: d.date,
    expected: d.expected,
    trained: d.trained ?? null,
    status: d.status,
  }));
  return adherenceWeeks(days).slice(-8);
}

export interface SplitDay {
  day: string;
  muscles: string;
  slots: Array<{ slot: number; moves: string[]; sets: number; muscles: string[]; focus: string[] }>;
}

export function programModel(snap: Snapshot): { sub: string; days: SplitDay[]; rotLine: string } {
  const rows = snap.split_active;
  const rot = snap.rotation || [];
  const byDay: Record<string, typeof rows> = {};
  rows.forEach(r => {
    (byDay[r.day] = byDay[r.day] || []).push(r);
  });
  const ordered = Object.keys(byDay).sort((a, b) => {
    const ia = rot.indexOf(a);
    const ib = rot.indexOf(b);
    if (ia >= 0 && ib >= 0) return ia - ib;
    if (ia >= 0) return -1;
    if (ib >= 0) return 1;
    return a < b ? -1 : 1;
  });
  const focus = prioMuscles(snap);
  const dayMuscles = (day: string) => {
    const seen: string[] = [];
    (byDay[day] || [])
      .slice()
      .sort((a, b) => a.slot - b.slot)
      .forEach(r => {
        (r.movements || '')
          .split('/')
          .map(m => m.trim())
          .forEach(m => {
            musclesOf(snap, m).forEach(mu => {
              if (seen.indexOf(mu) < 0) seen.push(mu);
            });
          });
      });
    return seen;
  };
  const days = ordered.map(day => ({
    day,
    muscles: dayMuscles(day).join(' · '),
    slots: (byDay[day] || [])
      .slice()
      .sort((a, b) => a.slot - b.slot)
      .map(r => {
        const moves = (r.movements || '').split('/').map(m => m.trim());
        const uniq = Array.from(new Set(moves.flatMap(m => musclesOf(snap, m))));
        return {
          slot: r.slot,
          moves,
          sets: r.sets,
          muscles: uniq,
          focus: uniq.filter(m => focus.has(m.toLowerCase())),
        };
      }),
  }));
  const seq = rot.length ? rot : ordered;
  return {
    sub: rot.length ? 'Active split, rotation: ' + rot.join(' / ') : 'Active split.',
    days,
    rotLine: rows.length
      ? 'Rotating ' + seq.join(' / ') + '.'
      : 'No program synced yet, split show in chat is the source.',
  };
}

export function prData(snap: Snapshot): PRData {
  return computePRs(snap.workouts, snap.sets);
}

export function topSetOn(
  sets: Snapshot['sets'],
  wdate: Record<number, string>,
  ex: string,
  date: string
): { w: number; r: number } | null {
  const day = sets.filter(
    s => s.exercise === ex && (wdate[s.workout_id] || s.created.slice(0, 10)) === date
  );
  if (!day.length) return null;
  const best = day.slice().sort((a, b) => e1rm(b.weight, b.reps) - e1rm(a.weight, a.reps))[0];
  return { w: best.weight, r: best.reps };
}

export function missedMap(snap: Snapshot): Record<string, string> {
  if (!snap.adherence) return missedExpected(null);
  return missedExpected({
    days: snap.adherence.days.map(d => ({ ...d, trained: d.trained ?? null })),
  });
}

export interface LiftMark {
  text: string;
  cls: string;
}

export function trendMarks(snap: Snapshot, lift: string, vals: Array<number | null>): LiftMark[] {
  const marks: LiftMark[] = [];
  const pts = (vals.filter(v => v !== null) as number[]).map(ev => ({ ev }));
  if (isStalling(pts)) marks.push({ text: 'stalling', cls: 'bad' });
  else if (deloadWatch(pts)) marks.push({ text: 'slipping', cls: 'bad' });
  const goals = snap.goals.map(g => String(g['exercise'] || '').toLowerCase());
  if (goals.includes(lift.toLowerCase())) marks.push({ text: 'goal', cls: 'plan' });
  return marks;
}

export { adherenceWeeks };
