// SSOT owner: UI-only selection over snapshot views. Consumers: pages.
// Search/facet/hidden state, tag-membership filtering, alphabetical sorts.
// No domain math: every number rendered here was computed in Python.

import type { Lift, SessionView } from '../generated/snapshot';
import { href } from '../routes';

export interface TrendMatrix {
  days: string[];
  series: Array<Array<number | null>>;
  top: string[];
}

export function liftByName(lifts: Lift[], exercise: string): Lift | null {
  const want = exercise.toLowerCase();
  return lifts.find(l => l.exercise.toLowerCase() === want) ?? null;
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

export function filterLifts(lifts: Lift[], q: string, facets: Set<string>): Lift[] {
  const query = (q || '').trim().toLowerCase();
  return lifts.filter(l => {
    if (query && !l.exercise.toLowerCase().includes(query)) return false;
    if (!facets.size) return true;
    const tags = new Set(l.tags);
    if (facets.has('goal') && tags.has('goal')) return true;
    if (facets.has('stall') && (tags.has('stalling') || tags.has('slipping'))) return true;
    if (facets.has('focus') && tags.has('focus')) return true;
    return false;
  });
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

export interface PageRow {
  key: string;
  label: string;
  sub: string;
  href: string;
}

export function palettePages(): PageRow[] {
  return [
    { key: 'dash', label: 'Dashboard', sub: 'overview', href: href.dash() },
    { key: 'lifts', label: 'Movements', sub: 'every lift', href: href.lifts() },
    { key: 'muscles', label: 'Muscles', sub: 'volume vs MEV', href: href.muscles() },
    { key: 'program', label: 'Program', sub: 'the split', href: href.program() },
  ];
}

export function filterPages(rows: PageRow[], q: string): PageRow[] {
  const needle = (q || '').trim().toLowerCase();
  if (!needle) return rows;
  return rows.filter(r => r.label.toLowerCase().includes(needle) || r.key.includes(needle));
}
