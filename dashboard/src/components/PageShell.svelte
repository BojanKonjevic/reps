<script lang="ts">
  // SSOT owner: page chrome. Consumers: every page (replaces 6 copies of the header).
  import Icon from './Icon.svelte';
  import { href } from '../routes';
  import type { Snippet } from 'svelte';

  interface Props {
    back?: boolean;
    children: Snippet;
  }

  let { back = false, children }: Props = $props();
</script>

<div class="sesstop">
  {#if back}
    <a class="iconbtn" href={href.dash()} aria-label="dashboard"><Icon name="home" /></a>
  {/if}
</div>
{@render children()}
