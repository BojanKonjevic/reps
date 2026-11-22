<script lang="ts">
  import type { BlockBodyweight, BlockWeightWindow } from '../generated/snapshot';
  import { fmtD } from '../lib/format';
  import Icon from './Icon.svelte';

  let { summary }: { summary: BlockBodyweight } = $props();
</script>

{#snippet endpoint(label: string, window: BlockWeightWindow)}
  <div class="endpoint">
    <span class="label">{label}</span>
    {#if window.kg !== null}
      <strong>{window.kg.toFixed(1)} <span class="unit">kg</span></strong>
    {:else}
      <span class="unavailable">Insufficient weigh-ins</span>
    {/if}
    {#if window.since && window.until}
      <span class="sample">
        {fmtD(window.since)}{window.since !== window.until ? ' to ' + fmtD(window.until) : ''}
        · {window.samples}
        {window.samples === 1 ? 'weigh-in' : 'weigh-ins'}
      </span>
    {/if}
  </div>
{/snippet}

<div class="weight-summary" role="group" aria-label="Block bodyweight">
  <div class="caption">Bodyweight</div>
  <div class="endpoints">
    {@render endpoint('Start', summary.start)}
    <span class="arrow" aria-hidden="true"><Icon name="chevronRight" size={14} /></span>
    {@render endpoint('End', summary.end)}
  </div>
</div>

<style>
  .weight-summary {
    margin-block: 10px 12px;
    border: 1px solid var(--line-soft);
    border-radius: var(--radius-sm);
    padding: 10px 12px 12px;
  }
  .caption {
    color: var(--ink-dim);
    font-size: 0.78rem;
    font-weight: 600;
    margin-bottom: 8px;
  }
  .endpoints {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
    align-items: start;
    gap: 8px;
  }
  .endpoint {
    display: grid;
    gap: 2px;
  }
  .label,
  .unit,
  .arrow,
  .sample,
  .unavailable {
    color: var(--ink-mute);
  }
  .label,
  .unit,
  .unavailable {
    font-size: 0.78rem;
  }
  .arrow {
    align-self: center;
  }
  .sample {
    font-size: 0.72rem;
  }
  strong {
    color: var(--ink);
    font-size: 1.45rem;
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.035em;
    line-height: 1.15;
  }
  .unit {
    letter-spacing: normal;
    font-weight: 500;
  }
</style>
