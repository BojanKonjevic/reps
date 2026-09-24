<script lang="ts">
  // SSOT owner: page chrome. Consumers: every page (replaces 6 copies of the header).
  import Icon from './Icon.svelte';
  import { href } from '../routes';
  import { route } from '../router.svelte';
  import type { Snippet } from 'svelte';

  interface Props {
    back?: boolean;
    children: Snippet;
  }

  let { back = false, children }: Props = $props();

  // Detail pages highlight their parent list; sessions stand alone.
  const active = $derived.by(() => {
    const v = route.view.name;
    if (v === 'lift' || v === 'lifts') return 'lifts';
    if (v === 'muscle' || v === 'muscles') return 'muscles';
    if (v === 'prog') return 'program';
    if (v === 'dash') return 'dash';
    return null;
  });
</script>

<nav class="topnav wrap" aria-label="primary">
  <a class="brand" href={href.dash()} aria-current={active === 'dash' ? 'page' : undefined}>reps</a>
  <a href={href.lifts()} aria-current={active === 'lifts' ? 'page' : undefined}>Movements</a>
  <a href={href.muscles()} aria-current={active === 'muscles' ? 'page' : undefined}>Muscles</a>
  <a href={href.program()} aria-current={active === 'program' ? 'page' : undefined}>Program</a>
</nav>
<div class="sesstop">
  {#if back}
    <a class="iconbtn" href={href.dash()} aria-label="dashboard"><Icon name="home" /></a>
  {/if}
</div>
{@render children()}
