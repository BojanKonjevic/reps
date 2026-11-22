<script lang="ts">
  import type { BlockBodyweight, BlockWeightWindow } from '../generated/snapshot';
  import Icon from './Icon.svelte';

  let { summary }: { summary: BlockBodyweight } = $props();
</script>

{#snippet endpoint(label: string, window: BlockWeightWindow)}
  <span class="endpoint">
    <span class="label">{label}</span>
    {#if window.kg !== null}
      <strong>{window.kg.toFixed(1)} <span class="unit">kg</span></strong>
    {:else}
      <span class="label">Insufficient weigh-ins</span>
    {/if}
  </span>
{/snippet}

<div class="weight-summary" role="group" aria-label="Block bodyweight">
  <span class="caption">Bodyweight</span>
  <div class="endpoints">
    {@render endpoint('Start', summary.start)}
    <span class="arrow" aria-hidden="true"><Icon name="chevronRight" size={12} /></span>
    {@render endpoint('End', summary.end)}
  </div>
</div>

<style>
  .weight-summary,
  .endpoints,
  .endpoint {
    display: flex;
    align-items: baseline;
  }
  .weight-summary,
  .endpoints {
    flex-wrap: wrap;
  }
  .weight-summary {
    gap: 3px 12px;
    margin-block: 10px 14px;
  }
  .endpoints {
    gap: 3px 8px;
  }
  .endpoint {
    gap: 4px;
  }
  .caption,
  .label,
  .unit,
  .arrow {
    color: var(--ink-mute);
    font-size: 0.76rem;
  }
  .caption {
    color: var(--ink-dim);
    font-weight: 600;
  }
  .arrow {
    align-self: center;
    display: inline-flex;
  }
  strong {
    color: var(--ink);
    font-size: 1.05rem;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  .unit {
    font-weight: 500;
  }
</style>
