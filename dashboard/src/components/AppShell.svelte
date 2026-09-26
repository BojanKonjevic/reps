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

  interface NavItem {
    key: string;
    label: string;
    icon: 'overview' | 'activity' | 'layers' | 'calendar' | 'clock';
    href: string;
  }

  // Single nav definition rendered twice (sidebar + topbar); destinations
  // come only from the route table in routes.ts.
  const nav: NavItem[] = [
    { key: 'dash', label: 'Overview', icon: 'overview', href: href.dash() },
    { key: 'lifts', label: 'Movements', icon: 'activity', href: href.lifts() },
    { key: 'muscles', label: 'Muscles', icon: 'layers', href: href.muscles() },
    { key: 'prog', label: 'Program', icon: 'calendar', href: href.program() },
    { key: 'hist', label: 'History', icon: 'clock', href: href.history() },
  ];

  const sectionOf: Record<string, string> = {
    dash: 'dash',
    sess: 'dash',
    lift: 'lifts',
    lifts: 'lifts',
    muscle: 'muscles',
    muscles: 'muscles',
    prog: 'prog',
    hist: 'hist',
  };

  const view = $derived(route.view.name);
  const navKey = $derived(sectionOf[view] ?? 'dash');
</script>

<div class="shell">
  <aside class="sidebar" aria-label="Primary">
    <a class="side-word" href={href.dash()}>reps</a>
    <nav class="sidenav">
      {#each nav as item}
        <a href={item.href} class:on={navKey === item.key}>
          <span class="side-ic"><Icon name={item.icon} size={15} /></span>{item.label}
        </a>
      {/each}
    </nav>
    <div class="side-meta"><span class="kbd">ctrl K</span> jump anywhere</div>
  </aside>
  <div class="maincol">
    <header class="topbar">
      <a class="side-word" href={href.dash()}>reps</a>
      <nav class="topnav" aria-label="Primary">
        {#each nav as item}
          <a href={item.href} class:on={navKey === item.key}>{item.label}</a>
        {/each}
      </nav>
    </header>
    <main class="content">
      <div class="page">
        {@render children()}
      </div>
    </main>
  </div>
</div>
