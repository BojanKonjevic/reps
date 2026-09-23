import { QueryClient } from '@tanstack/svelte-query';

// Single coherent snapshot query. Server state lives here, never copied
// into unrelated component state; refresh via invalidation, never a
// bespoke reload mechanism. The sync layer (sync_push) publishes state;
// this query only reads it.

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
});

export const snapshotKey = ['snapshot'] as const;
