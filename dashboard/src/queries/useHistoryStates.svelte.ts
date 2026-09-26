import { createQuery } from '@tanstack/svelte-query';
import { queryClient } from './client';
import { fetchHistoryStates, historyStatesKey } from './historyStates';

// Component-context wrapper: call during component initialization, exactly
// like createQuery in App.svelte. The pure fetch and key stay testable in
// historyStates.ts without the svelte-query runtime.
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
