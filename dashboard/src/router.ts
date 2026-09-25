// SSOT owner: hash routing view mapping. Consumers: App via router.svelte.
// Address parsing lives in routes.ts; this module only maps routes to views.

import { parse, isDate, type Route } from './routes';

export type View =
  | { name: 'dash' }
  | { name: 'sess'; date: string }
  | { name: 'lift'; exercise: string }
  | { name: 'muscle'; muscle: string }
  | { name: 'prog' }
  | { name: 'lifts' }
  | { name: 'muscles' }
  | { name: 'hist' };

export { isDate };

export function parseHash(hash: string): View {
  const r: Route = parse(hash || '');
  if (r.name === 'lift') return { name: 'lift', exercise: r.exercise };
  if (r.name === 'session') {
    if (isDate(r.date)) return { name: 'sess', date: r.date };
    return { name: 'dash' };
  }
  if (r.name === 'muscle') return { name: 'muscle', muscle: r.muscle };
  if (r.name === 'program') return { name: 'prog' };
  if (r.name === 'lifts') return { name: 'lifts' };
  if (r.name === 'muscles') return { name: 'muscles' };
  if (r.name === 'history') return { name: 'hist' };
  return { name: 'dash' };
}
