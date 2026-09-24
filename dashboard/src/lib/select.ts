// SSOT owner: UI-only selection over snapshot views. Consumers: pages.
// Search/facet/hidden state, tag-membership filtering, alphabetical sorts.
// No domain math: every number rendered here was computed in Python.

import type { Lift } from '../generated/snapshot';

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
