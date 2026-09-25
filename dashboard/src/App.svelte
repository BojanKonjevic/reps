<script lang="ts">
  import { QueryClientProvider } from '@tanstack/svelte-query';
  import { createQuery } from '@tanstack/svelte-query';
  import { onMount } from 'svelte';
  import { queryClient, snapshotKey } from './queries/client';
  import { fetchSnapshot } from './queries/snapshot';
  import { syncRoute, route } from './router.svelte';
  import { closePalette, palette } from './lib/palette.svelte';
  import CommandPalette from './components/CommandPalette.svelte';
  import DashboardPage from './pages/DashboardPage.svelte';
  import SessionPage from './pages/SessionPage.svelte';
  import LiftPage from './pages/LiftPage.svelte';
  import MusclePage from './pages/MusclePage.svelte';
  import ProgramPage from './pages/ProgramPage.svelte';
  import LiftsPage from './pages/LiftsPage.svelte';
  import MusclesPage from './pages/MusclesPage.svelte';

  const snapshot = createQuery(
    () => ({ queryKey: snapshotKey, queryFn: fetchSnapshot }),
    () => queryClient
  );

  onMount(() => {
    // The router owns scroll position per hash; the browser must not race it.
    history.scrollRestoration = 'manual';
    syncRoute();
    const keys = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        palette.open = !palette.open;
      } else if (e.key === 'Escape' && palette.open) {
        // Single source for esc: capture phase beats focus and delegation
        // order puzzles, and the input no longer handles it at all.
        e.preventDefault();
        e.stopPropagation();
        closePalette();
      }
    };
    window.addEventListener('hashchange', syncRoute);
    window.addEventListener('keydown', keys, true);
    return () => {
      window.removeEventListener('hashchange', syncRoute);
      window.removeEventListener('keydown', keys, true);
    };
  });
</script>

<QueryClientProvider client={queryClient}>
  {#if snapshot.isPending}
    <div class="wrap">
      <h1>Training dashboard</h1>
      <div class="sub">loading</div>
    </div>
  {:else if snapshot.isError}
    <div class="wrap">
      <h1>Training dashboard</h1>
      <div class="sub">snapshot failed validation: {snapshot.error.message}</div>
    </div>
  {:else if snapshot.data}
    {@const snap = snapshot.data}
    <CommandPalette {snap} />
    {#if route.view.name === 'sess'}
      <SessionPage {snap} date={route.view.date} />
    {:else if route.view.name === 'lift'}
      <LiftPage {snap} exercise={route.view.exercise} />
    {:else if route.view.name === 'muscle'}
      <MusclePage {snap} muscle={route.view.muscle} />
    {:else if route.view.name === 'prog'}
      <ProgramPage {snap} />
    {:else if route.view.name === 'lifts'}
      <LiftsPage {snap} />
    {:else if route.view.name === 'muscles'}
      <MusclesPage {snap} />
    {:else}
      <DashboardPage {snap} />
    {/if}
  {/if}
</QueryClientProvider>
