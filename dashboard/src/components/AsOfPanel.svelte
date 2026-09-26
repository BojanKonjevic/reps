<script lang="ts">
  // SSOT owner: as-of panel shell. Consumers: pages with historical states.
  // Date cursor in, one of loading/unavailable/bundle out; the chart above
  // stays visible throughout. Scope comes from the selected event or the
  // page; the bundle comes from on-demand history states.
  import { fmtD } from '../lib/format';
  import { selectStateForDate, type EventScope } from '../lib/temporal';
  import type { HistoryState } from '../generated/historyStates';
  import type { Snapshot } from '../generated/snapshot';
  import TrainingState from './TrainingState.svelte';

  interface Props {
    snap: Snapshot;
    date: string | null;
    scope: EventScope;
    ruleId: number | null;
    states: HistoryState[] | null;
    loading: boolean;
    rangeMin: string | null;
    id?: string;
  }

  let { snap, date, scope, ruleId, states, loading, rangeMin, id = undefined }: Props = $props();

  const bundle = $derived(date && states ? selectStateForDate(states, date) : null);
</script>

{#if date}
  <div class="asofwrap" {id}>
    {#if loading}
      <div class="asof">
        <div><b>Training state</b> <span class="meta">As of {fmtD(date)} · historical</span></div>
        <div class="cap">Loading historical state…</div>
      </div>
    {:else if !states || !bundle}
      <div class="asof">
        <div><b>Training state</b> <span class="meta">As of {fmtD(date)} · historical</span></div>
        {#if rangeMin && date < rangeMin}
          <div class="cap">Historical state unavailable before {fmtD(rangeMin)}.</div>
        {:else}
          <div class="cap">Historical state unavailable.</div>
        {/if}
      </div>
    {:else}
      <TrainingState histState={bundle} {date} {snap} {scope} {ruleId} />
    {/if}
  </div>
{/if}
