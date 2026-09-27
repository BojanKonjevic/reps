import { createQuery } from '@tanstack/svelte-query';
import { queryClient } from './client';
import { fetchHistoryStates, historyStatesKey } from './historyStates';

// Component-context wrapper: call during component initialization, exactly
// like createQuery in App.svelte. The pure fetch and key stay testable in
// historyStates.ts without the svelte-query runtime.
// Reactivity note: the options thunk re-runs when its tracked deps change,
// so enabled()/exported() inside it stay live (not one-shot eager eval).
// history-states are immutable per export, hence staleTime Infinity keyed
// by exported; gcTime stays default (a new export creates a new key).
export function useHistoryStates(enabled: () => boolean, exported: () => string) {
  return createQuery(
    () => ({
      queryKey: historyStatesKey(exported()),
      queryFn: fetchHistoryStates,
      staleTime: Infinity,
      enabled: enabled(),
    }),
    () => queryClient
  );
}
