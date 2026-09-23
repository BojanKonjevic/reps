<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtD } from '../utils';
  import { GROUPS, MC } from '../charts';
  import { musclePageData } from '../forward';
  import type { Snapshot } from '../schemas/snapshot';
  import { ui } from '../lib/filters.svelte';
  import MuscleVolumeChart from '../components/MuscleVolumeChart.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const vol = $derived(snap.volume || null);
  const grouped = $derived((snap.autoreg?.grouped || {}) as Record<string, string[]>);

  function tierOf(m: string): string | null {
    const t = snap.priority[m] as string | { tier?: string } | undefined;
    return typeof t === 'string' ? t : t ? t.tier || null : null;
  }

  function bad(m: string): boolean {
    const v = vol?.[m];
    return !!v && (v.status === 'below_mev' || v.status === 'above_mrv');
  }

  function musPasses(m: string): boolean {
    if (!ui.muscleFacets.size) return true;
    const v = vol?.[m];
    const status = v ? v.status : 'in_range';
    const tier = tierOf(m);
    for (const f of ui.muscleFacets) {
      if (f === 'below' && status === 'below_mev') return true;
      if (f === 'above' && status === 'above_mrv') return true;
      if (f === 'priority' && tier === 'priority') return true;
      if (f === 'grouped' && grouped[m]) return true;
    }
    return false;
  }

  const order = $derived(
    GROUPS.slice().sort((a, b) => {
      const ba = bad(a) ? 0 : 1;
      const bb = bad(b) ? 0 : 1;
      if (ba !== bb) return ba - bb;
      const ta = tierOf(a);
      const tb = tierOf(b);
      const pa = ta && ta !== 'maintain' ? 0 : 1;
      const pb = tb && tb !== 'maintain' ? 0 : 1;
      if (pa !== pb) return pa - pb;
      return a < b ? -1 : 1;
    })
  );

  const shown = $derived(order.filter(m => musPasses(m)));

  const wlabels = $derived.by(() => {
    const mon = new Date();
    mon.setHours(12, 0, 0, 0);
    mon.setDate(mon.getDate() - ((mon.getDay() + 6) % 7));
    return [7, 6, 5, 4, 3, 2, 1, 0].map(k =>
      fmtD(new Date(mon.getTime() - k * 7 * 86400000).toISOString().slice(0, 10))
    );
  });

  interface Mark {
    text: string;
    cls: string;
  }

  function marksFor(m: string): Mark[] {
    const marks: Mark[] = [];
    const entry = vol?.[m];
    if (entry) {
      if (entry.status === 'below_mev') marks.push({ text: 'below MEV', cls: 'bad' });
      else if (entry.status === 'above_mrv') marks.push({ text: 'above MRV', cls: 'bad' });
      else marks.push({ text: 'in range', cls: '' });
    }
    const tier = tierOf(m);
    if (tier && tier !== 'maintain')
      marks.push({ text: tier, cls: tier === 'priority' ? 'plan' : '' });
    if (grouped[m]) marks.push({ text: 'grouped fatigue: ' + grouped[m].join(', '), cls: 'bad' });
    return marks;
  }

  onMount(() => {
    document.title = 'muscles';
    window.scrollTo(0, 0);
  });
</script>

<div class="wrap" id="viewMuscles">
  <div class="sesstop">
    <a class="iconbtn" href="#/" aria-label="dashboard"
      ><svg viewBox="0 0 16 16" width="22" height="22">
        <path
          d="M2.5 8 8 2.5 13.5 8M4.5 6.5v7h7v-7M7 13.5v-3h2v3"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        /></svg
      ></a
    >
  </div>
  <h1>Muscles</h1>
  <div class="sub" id="musSub2">
    {#if !vol}no volume data, sync first{:else}{shown.length} muscles{/if}
  </div>
  <div class="card">
    <div class="filterbar">
      <span class="legend" id="musFacets">
        {#each [['Below MEV', 'below'], ['Above MRV', 'above'], ['Priority', 'priority'], ['Grouped', 'grouped']] as [label, facet]}
          <button
            type="button"
            class="chip mini"
            class:off={!ui.muscleFacets.has(facet)}
            data-facet={facet}
            aria-pressed={ui.muscleFacets.has(facet)}
            onclick={() => {
              if (ui.muscleFacets.has(facet)) ui.muscleFacets.delete(facet);
              else ui.muscleFacets.add(facet);
            }}>{label}</button
          >
        {/each}
      </span>
    </div>
    <div class="listgrid" id="musGrid">
      {#if vol}
        {#each shown as m}
          {@const entry = vol[m] || { weekly: [], mev: 0, mav: null, mrv: null }}
          {@const data = musclePageData(snap.workouts, snap.sets, m)}
          {@const lifts = data.lifts || []}
          <div
            class="card"
            style="margin: 0"
            role="link"
            tabindex="0"
            onclick={ev => {
              if ((ev.target as HTMLElement).tagName !== 'A')
                location.hash = '#/m/' + encodeURIComponent(m);
            }}
            onkeydown={ev => {
              if (ev.key === 'Enter') location.hash = '#/m/' + encodeURIComponent(m);
            }}
          >
            <div class="listrow">
              <div class="listinfo">
                <div class="minititle">
                  <a href="#/m/{encodeURIComponent(m)}">{m}</a>
                  <span class="ministat">
                    {#each marksFor(m) as x}
                      <span class={'minisub ' + x.cls}>{x.text}</span>
                    {/each}
                  </span>
                </div>
                {#each lifts.slice(0, 3) as l}
                  <div class="cap">
                    <a href="#/l/{encodeURIComponent(l.ex)}">{l.ex}</a>
                    <span> {l.sets} sets · {Math.round(l.share * 100)}%</span>
                  </div>
                {/each}
                {#if lifts.length > 3}
                  <div class="cap">
                    <a href="#/m/{encodeURIComponent(m)}">+{lifts.length - 3} more</a>
                  </div>
                {/if}
              </div>
              <div class="listchart">
                <MuscleVolumeChart
                  labels={wlabels}
                  counts={entry.weekly || []}
                  bands={{
                    mev: entry.mev !== undefined ? entry.mev : 0,
                    mav: entry.mav || null,
                    mrv: entry.mrv !== undefined ? entry.mrv : null,
                  }}
                  color={MC[m] || '#888'}
                  height="120px"
                />
              </div>
            </div>
          </div>
        {/each}
      {/if}
    </div>
    <div class="cap">Weekly sets against MEV/MAV/MRV. Tap a muscle for the full page.</div>
  </div>
</div>
