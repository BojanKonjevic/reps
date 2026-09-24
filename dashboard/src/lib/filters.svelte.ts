// UI state for filters and lift visibility. Server state belongs to the
// snapshot query; this is client-only UI state (search text, facet sets,
// hidden lifts persisted to localStorage). One state object so pages and
// components mutate properties (imported bindings cannot be reassigned).
// Sets use SvelteSet so add/delete notify subscribers.

import { SvelteSet } from 'svelte/reactivity';

function readStored(): { hidden: string[]; touched: boolean } {
  try {
    const raw = localStorage.getItem('reps-hidden');
    if (raw !== null) return { hidden: JSON.parse(raw) as string[], touched: true };
  } catch {
    // storage unavailable, start fresh
  }
  return { hidden: [], touched: false };
}

const stored = readStored();

interface UiState {
  trendQ: string;
  trendFacets: SvelteSet<string>;
  liftQ: string;
  liftFacets: SvelteSet<string>;
  muscleFacets: SvelteSet<string>;
  hidden: SvelteSet<string>;
  hiddenTouched: boolean;
}

export const ui: UiState = $state({
  trendQ: '',
  trendFacets: new SvelteSet<string>(),
  liftQ: '',
  liftFacets: new SvelteSet<string>(),
  muscleFacets: new SvelteSet<string>(),
  hidden: new SvelteSet(stored.hidden),
  hiddenTouched: stored.touched,
});

function persist() {
  try {
    localStorage.setItem('reps-hidden', JSON.stringify(Array.from(ui.hidden)));
  } catch {
    // storage unavailable, ignore
  }
}

// Prune saved names missing from the snapshot, on load.
export function pruneHidden(known: string[]) {
  for (const n of Array.from(ui.hidden)) if (!known.includes(n)) ui.hidden.delete(n);
  persist();
}

// First visit hides everything past the default visible cutoff from
// snapshot constants (trend_top_lifts); afterwards the saved picks rule.
export function defaultHide(names: string[], cutoff = 8) {
  if (!ui.hiddenTouched) names.slice(cutoff).forEach(n => ui.hidden.add(n));
  persist();
}

export function toggleHidden(name: string) {
  ui.hiddenTouched = true;
  if (ui.hidden.has(name)) ui.hidden.delete(name);
  else ui.hidden.add(name);
  persist();
}

export function showAllLifts() {
  ui.hiddenTouched = true;
  ui.hidden.clear();
  ui.trendQ = '';
  ui.trendFacets.clear();
  persist();
}

export function hideAllLifts(names: string[]) {
  ui.hiddenTouched = true;
  names.forEach(t => ui.hidden.add(t));
  persist();
}

export function resetTrend() {
  ui.hiddenTouched = true;
  ui.trendQ = '';
  ui.trendFacets.clear();
  ui.hidden.clear();
  persist();
}
