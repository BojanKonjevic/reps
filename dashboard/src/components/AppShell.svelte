<script lang="ts">
  // SSOT owner: page chrome. Consumers: App.svelte (once, around every page).
  // Persistent sidebar on desktop, compact top nav on narrow layouts.
  // Destinations map only to the current route table in routes.ts.
  import Icon from './Icon.svelte';
  import { href } from '../routes';
  import { route } from '../router.svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    children: Snippet;
  }

  let { children }: Props = $props();

  const view = $derived(route.view.name);
  const navKey = $derived(
    view === 'dash' || view === 'sess'
      ? 'dash'
      : view === 'lift' || view === 'lifts'
        ? 'lifts'
        : view === 'muscle' || view === 'muscles'
          ? 'muscles'
          : view === 'prog'
            ? 'prog'
            : 'hist'
  );
</script>

<div class="shell">
  <aside class="sidebar" aria-label="Primary">
    <a class="side-word" href={href.dash()}>reps</a>
    <nav class="sidenav">
      <a href={href.dash()} class:on={navKey === 'dash'}>
        <span class="side-ic"><Icon name="overview" size={15} /></span>Overview
      </a>
      <a href={href.lifts()} class:on={navKey === 'lifts'}>
        <span class="side-ic"><Icon name="activity" size={15} /></span>Movements
      </a>
      <a href={href.muscles()} class:on={navKey === 'muscles'}>
        <span class="side-ic"><Icon name="layers" size={15} /></span>Muscles
      </a>
      <a href={href.program()} class:on={navKey === 'prog'}>
        <span class="side-ic"><Icon name="calendar" size={15} /></span>Program
      </a>
      <a href={href.history()} class:on={navKey === 'hist'}>
        <span class="side-ic"><Icon name="clock" size={15} /></span>History
      </a>
    </nav>
    <div class="side-meta"><span class="kbd">ctrl K</span> jump anywhere</div>
  </aside>
  <div class="maincol">
    <header class="topbar">
      <a class="side-word" href={href.dash()}>reps</a>
      <nav class="topnav" aria-label="Primary">
        <a href={href.dash()} class:on={navKey === 'dash'}>Overview</a>
        <a href={href.lifts()} class:on={navKey === 'lifts'}>Movements</a>
        <a href={href.muscles()} class:on={navKey === 'muscles'}>Muscles</a>
        <a href={href.program()} class:on={navKey === 'prog'}>Program</a>
        <a href={href.history()} class:on={navKey === 'hist'}>History</a>
      </nav>
    </header>
    <main class="content">
      <div class="page">
        {@render children()}
      </div>
    </main>
  </div>
</div>
