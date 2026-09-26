<script lang="ts">
  // SSOT owner: history page. Consumers: `#/history` route alone.
  import { onMount } from 'svelte';
  import { SvelteSet } from 'svelte/reactivity';
  import { fmtD } from '../lib/format';
  import {
    domainLabel,
    filterHistory,
    historyOf,
    ruleIdOf,
    scopeOf,
    stateOn,
    type HistoryEvent,
  } from '../lib/temporal';
  import { createEventSelection } from '../lib/eventSelection.svelte';
  import type { Snapshot } from '../generated/snapshot';
  import PageShell from '../components/PageShell.svelte';
  import ChangeDetail from '../components/ChangeDetail.svelte';
  import TrainingState from '../components/TrainingState.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const events = $derived(historyOf(snap));
  const domains = $derived(Array.from(new Set(events.map(e => e.domain))).sort());

  let picked = $state(new SvelteSet<string>());
  let seeded = $state('');
  let from = $state('');
  let to = $state('');

  const sel = createEventSelection();

  $effect(() => {
    const key = domains.join(','); // sanctioned: SvelteSet change-key for filter reseed, not a DB column split
    if (key !== seeded) {
      seeded = key;
      picked = new SvelteSet(domains);
    }
  });

  const listed = $derived(filterHistory(events, picked, from, to));
  const selected = $derived(listed.find(e => e.id === sel.selId) ?? null);
  const histState = $derived(sel.stateDate ? stateOn(snap, sel.stateDate) : null);

  function toggleDomain(d: string) {
    if (picked.has(d)) picked.delete(d);
    else picked.add(d);
  }

  onMount(() => {
    document.title = 'history';
  });
</script>

<PageShell back>
  <div class="wrap" id="viewHistory">
    <h1>History</h1>
    <div class="sub" id="histSub">
      {events.length
        ? events.length + ' recorded training-system changes'
        : 'no recorded changes yet, edits in chat start the trail'}
    </div>
    {#if events.length}
      <div class="card">
        <div class="histfilters" id="histFilters">
          <span class="legend">
            {#each domains as d}
              <button
                type="button"
                class="chip"
                class:off={!picked.has(d)}
                aria-pressed={picked.has(d)}
                onclick={() => toggleDomain(d)}
              >
                {domainLabel(d)}
              </button>
            {/each}
          </span>
          <label>from <input type="date" aria-label="from date" bind:value={from} /></label>
          <label>to <input type="date" aria-label="to date" bind:value={to} /></label>
        </div>
        <div id="histList">
          {#each listed as e}
            <div class="histrow">
              <div class="hhead">
                <span class="hdate">{fmtD(e.date)}</span>
                <span class="cdomain">{domainLabel(e.domain)}</span>
                <button
                  type="button"
                  class="evbtn"
                  onclick={() => sel.select(e.id)}
                  aria-pressed={sel.selId === e.id}
                >
                  <b>{e.title}</b>
                </button>
              </div>
              <div class="hsum">{e.summary}</div>
              {#if selected && selected.id === e.id}
                {@const ev: HistoryEvent = selected}
                <ChangeDetail
                  event={ev}
                  {events}
                  stateOpen={sel.stateDate === ev.date}
                  onViewState={sel.viewState}
                />
                {#if histState && sel.stateDate === ev.date}
                  <TrainingState {histState} {snap} scope={scopeOf(ev)} ruleId={ruleIdOf(ev)} />
                {/if}
              {/if}
            </div>
          {:else}
            <div class="empty">nothing matches, loosen the filters</div>
          {/each}
        </div>
      </div>
    {/if}
  </div>
</PageShell>
