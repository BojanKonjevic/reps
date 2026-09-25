<script lang="ts">
  // SSOT owner: as-of date control. Consumers: lift and muscle pages.
  // Today is the default (the charts themselves); recorded event dates are
  // the only historical options because the frontend never folds chains.
  import { fmtD } from '../lib/format';

  interface Props {
    dates: string[];
    value: string | null;
    onPick: (date: string | null) => void;
    id?: string;
  }

  let { dates, value, onPick, id = undefined }: Props = $props();
</script>

{#if dates.length}
  <div class="evstrip" {id} aria-label="As of date">
    <span class="cap" style="margin: 0">As of:</span>
    <button
      type="button"
      class="evbtn"
      class:sel={value === null}
      aria-pressed={value === null}
      onclick={() => onPick(null)}
    >
      Today
    </button>
    {#each dates as date}
      <button
        type="button"
        class="evbtn"
        class:sel={value === date}
        aria-pressed={value === date}
        onclick={() => onPick(date === value ? null : date)}
      >
        <span class="evdate">{fmtD(date)}</span>
      </button>
    {/each}
  </div>
{/if}
