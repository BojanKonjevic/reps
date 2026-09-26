// SSOT owner: UI-only selection over snapshot views. Consumers: pages.
// Search/facet/hidden state, tag-membership filtering, alphabetical sorts.
// No domain math: every number rendered here was computed in Python.

import type { AutoregChange, AutoregHold, Lift, Muscle, SessionView } from '../generated/snapshot';
import { href } from '../routes';
import { fmtD, fmtMin, fmtV } from './format';
import { statusLabel } from './present';

export interface TrendMatrix {
  days: string[];
  series: Array<Array<number | null>>;
  top: string[];
}

export function liftByName(lifts: Lift[], exercise: string): Lift | null {
  const want = exercise.toLowerCase();
  return lifts.find(l => l.exercise.toLowerCase() === want) ?? null;
}

export function latestE1rm(lifts: Lift[], exercise: string): string {
  // Latest session e1RM for small-multiple headers; the value is emitted,
  // this only selects and formats it.
  const sess = liftByName(lifts, exercise)?.sessions;
  if (!sess || !sess.length) return '';
  return fmtV(sess[sess.length - 1].e1rm);
}

export function defaultOrder(lifts: Lift[]): Lift[] {
  return lifts.slice().sort((a, b) => a.rank_default - b.rank_default);
}

export function attentionOrder(lifts: Lift[]): Lift[] {
  return lifts.slice().sort((a, b) => a.rank_attention - b.rank_attention);
}

export function trendMatrix(lifts: Lift[]): TrendMatrix {
  const ordered = defaultOrder(lifts);
  const daySet = new Set<string>();
  for (const l of ordered) for (const s of l.sessions) daySet.add(s.date);
  const days = Array.from(daySet).sort();
  const series = ordered.map(l => {
    const byDate = new Map(l.sessions.map(s => [s.date, s.e1rm]));
    return days.map(d => byDate.get(d) ?? null);
  });
  return { days, series, top: ordered.map(l => l.exercise) };
}

export function tagFacetsPass(tags: Set<string>, facets: Set<string>): boolean {
  // Goal/stalling/focus core shared by the trend filter and the movement
  // index; autoreg/grouped facets live in movementPasses below.
  for (const f of facets) {
    if (f === 'goal' && tags.has('goal')) return true;
    if (f === 'stall' && (tags.has('stalling') || tags.has('slipping'))) return true;
    if (f === 'focus' && tags.has('focus')) return true;
  }
  return false;
}

export interface MovementIndexInput {
  lifts: Lift[];
  holds: AutoregHold[];
  changes: AutoregChange[];
  grouped: Record<string, string[]>;
}

function normMove(m: string): string {
  return m.trim().toLowerCase();
}

export function heldMovements(holds: AutoregHold[]): Set<string> {
  const out = new Set<string>();
  for (const h of holds) for (const m of h.moves) if (normMove(m)) out.add(normMove(m));
  return out;
}

export function changedMovements(changes: AutoregChange[]): Set<string> {
  const out = new Set<string>();
  for (const ch of changes) {
    if (ch.reverted_on) continue;
    for (const m of ch.after_moves) if (normMove(m)) out.add(normMove(m));
  }
  return out;
}

export function groupedMusclesOf(grouped: Record<string, string[]>, exercise: string): string[] {
  const out: string[] = [];
  for (const [mus, lifts] of Object.entries(grouped)) {
    if (lifts.some(l => l.toLowerCase() === exercise.toLowerCase())) out.push(mus);
  }
  return out;
}

export function changeForMovement(
  changes: AutoregChange[],
  exercise: string
): AutoregChange | null {
  const low = exercise.toLowerCase();
  for (const ch of changes) {
    if (ch.reverted_on) continue;
    if (ch.after_moves.map(normMove).includes(low)) return ch;
  }
  return null;
}

export function movementRank(
  lifts: Lift[],
  exercise: string,
  held: Set<string>,
  changed: Set<string>
): number {
  if (held.has(exercise.toLowerCase()) || changed.has(exercise.toLowerCase())) return 0;
  const tags = new Set(liftByName(lifts, exercise)?.tags ?? []);
  if (tags.has('stalling') || tags.has('slipping')) return 1;
  if (tags.has('goal')) return 2;
  return 3;
}

export function movementPasses(
  lifts: Lift[],
  exercise: string,
  q: string,
  facets: Set<string>,
  ctx: { held: Set<string>; changed: Set<string>; grouped: Record<string, string[]> }
): boolean {
  if (q && !exercise.toLowerCase().includes(q)) return false;
  if (!facets.size) return true;
  const low = exercise.toLowerCase();
  const tags = new Set(liftByName(lifts, exercise)?.tags ?? []);
  for (const f of facets) {
    if (f === 'autoreg' && (ctx.held.has(low) || ctx.changed.has(low))) return true;
    if (f === 'grouped' && groupedMusclesOf(ctx.grouped, exercise).length) return true;
  }
  return tagFacetsPass(tags, facets);
}

export function orderMovementIndex(
  input: MovementIndexInput,
  q: string,
  facets: Set<string>
): Lift[] {
  const held = heldMovements(input.holds);
  const changed = changedMovements(input.changes);
  const query = (q || '').trim().toLowerCase();
  const ctx = { held, changed, grouped: input.grouped };
  return input.lifts
    .slice()
    .sort(
      (a, b) =>
        movementRank(input.lifts, a.exercise, held, changed) -
          movementRank(input.lifts, b.exercise, held, changed) || (a.exercise < b.exercise ? -1 : 1)
    )
    .filter(l => movementPasses(input.lifts, l.exercise, query, facets, ctx));
}

export function sortAlpha<T extends string>(names: T[]): T[] {
  return names.slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export interface SessionSpan {
  date: string;
  minutes: number;
  day: string;
}

export function sessionSpans(sessions: SessionView[]): SessionSpan[] {
  // Done sessions with a derived span only: open workouts are partial,
  // rest rows carry no sets. Unmatched days group under one label.
  return sessions
    .filter(s => s.status === 'done' && s.duration_min !== null && s.duration_min !== undefined)
    .map(s => ({
      date: s.date,
      minutes: s.duration_min as number,
      day: s.slot_label || 'unscheduled',
    }))
    .sort((a, b) => (a.date < b.date ? -1 : 1));
}

export interface PalRow {
  key: string;
  label: string;
  sub: string;
  href: string;
  match: string;
}

export interface PalSection {
  header: string;
  rows: PalRow[];
}

function palRow(key: string, label: string, sub: string, target: string, match: string): PalRow {
  return { key, label, sub, href: target, match: (label + ' ' + match).toLowerCase() };
}

export function palettePages(): PalRow[] {
  return [
    palRow('page:dash', 'Dashboard', 'overview', href.dash(), 'dash'),
    palRow('page:lifts', 'Movements', 'every lift', href.lifts(), 'lifts'),
    palRow('page:muscles', 'Muscles', 'volume vs MEV', href.muscles(), 'muscles'),
    palRow('page:program', 'Program', 'the split', href.program(), 'program'),
    palRow('page:history', 'History', 'recorded changes', href.history(), 'history'),
  ];
}

export function paletteMovements(lifts: Lift[]): PalRow[] {
  return lifts
    .map(l =>
      palRow(
        'lift:' + l.exercise,
        l.exercise,
        l.best ? 'e1RM ' + fmtV(l.best.e1rm) + ' · ' + fmtD(l.best.date) : 'no sets yet',
        href.lift(l.exercise),
        l.exercise
      )
    )
    .sort((a, b) => (a.label < b.label ? -1 : 1));
}

export function paletteMuscles(muscles: Muscle[]): PalRow[] {
  return muscles
    .map(m => {
      const wk = m.weekly.length ? m.weekly[m.weekly.length - 1] : 0;
      return palRow(
        'muscle:' + m.muscle,
        m.muscle,
        statusLabel(m.status) + ' · ' + wk + (wk === 1 ? ' set' : ' sets'),
        href.muscle(m.muscle),
        m.muscle
      );
    })
    .sort((a, b) => (a.label < b.label ? -1 : 1));
}

export function paletteSessions(sessions: SessionView[]): PalRow[] {
  return sessions
    .filter(s => s.status === 'done' || s.status === 'rest')
    .sort((a, b) => (a.date > b.date ? -1 : 1))
    .map(s => {
      const day = s.slot_label || 'unscheduled';
      const sub =
        s.status === 'rest'
          ? 'rest day'
          : day +
            ' · ' +
            s.exercises.reduce((a, e) => a + e.sets.length, 0) +
            ' sets' +
            (s.duration_min === null || s.duration_min === undefined
              ? ''
              : ' · ' + fmtMin(s.duration_min));
      return palRow(
        'session:' + s.date,
        fmtD(s.date),
        sub,
        href.session(s.date),
        s.date + ' ' + day
      );
    });
}

export function filterPalRows(rows: PalRow[], q: string, limit = 6): PalRow[] {
  const needle = (q || '').trim().toLowerCase();
  if (!needle) return rows.slice(0, limit);
  return rows.filter(r => r.match.includes(needle)).slice(0, limit);
}
