import { historyStatesSchema, type HistoryStates } from '../generated/historyStates';

// On-demand historical states: fetched when the user opens as-of UI, never
// part of the snapshot payload. Keyed by the snapshot export stamp, cached
// forever (append-only history cannot contradict itself), invalidated
// automatically when a newer sync arrives under a new stamp.

export const historyStatesKey = (exported: string) => ['history-states', exported] as const;

export async function fetchHistoryStates(): Promise<HistoryStates | null> {
  const res = await fetch('/history-states');
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('history-states fetch failed: ' + res.status);
  return historyStatesSchema.parse(await res.json());
}
