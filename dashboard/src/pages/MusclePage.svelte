<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtV } from '../utils';
  import { GROUPS } from '../charts';
  import { musclePageData } from '../forward';
  import type { Snapshot } from '../schemas/snapshot';
  import { prioMuscles } from '../lib/dashboard';
  import type { PieSlice } from '../pieChart';
  import { piePalette } from '../pieChart';
  import MuscleVolumeChart from '../components/MuscleVolumeChart.svelte';
  import MusclePie from '../components/MusclePie.svelte';

  interface Props {
    snap: Snapshot;
    muscle: string;
  }

  let { snap, muscle: requested }: Props = $props();

  const match = $derived(GROUPS.filter(g => g.toLowerCase() === requested.toLowerCase())[0]);

  const data = $derived(match ? musclePageData(snap.workouts, snap.sets, match) : null);
  const entry = $derived(
    (match
      ? (snap.constants?.muscles[match] as
          | { mev?: number; mav?: [number, number] | null; mrv?: number | null; color?: string }
          | undefined)
      : undefined) || {}
  );

  const sub = $derived.by(() => {
    if (!match || !data) return '';
    const mav = entry.mav ? entry.mav[0] + '-' + entry.mav[1] : 'no range';
    const mrv = entry.mrv !== undefined && entry.mrv !== null ? entry.mrv : 'no cap';
    const recent = data.counts.slice(-4);
    const avg = recent.length ? recent.reduce((a, b) => a + b, 0) / recent.length : 0;
    const last8 = data.counts.slice(-8);
    const trained = last8.filter(c => c > 0).length;
    const isFocus = prioMuscles(snap).has(match.toLowerCase());
    return (
      'MEV ' +
      (entry.mev !== undefined ? entry.mev : '?') +
      ' · MAV ' +
      mav +
      ' · MRV ' +
      mrv +
      ' · last 4 weeks avg ' +
      fmtV(Math.round(avg * 10) / 10) +
      '/wk · trained ' +
      trained +
      ' of last ' +
      last8.length +
      ' weeks' +
      (isFocus ? ' · focus' : '')
    );
  });

  const slices = $derived.by((): PieSlice[] => {
    if (!data) return [];
    const ranked = data.lifts;
    const big = ranked.filter(l => l.share >= 0.04);
    const small = ranked.filter(l => l.share < 0.04);
    const smallSets = small.reduce((a, l) => a + l.sets, 0);
    const out: PieSlice[] = big.map(l => ({
      label: l.ex,
      frac: l.share,
      link: '#/l/' + encodeURIComponent(l.ex),
    }));
    if (smallSets > 0) {
      out.push({
        label: small.length + ' smaller lifts',
        frac: smallSets / (data.total || 1),
        link: null,
      });
    }
    return out;
  });

  const sliceSets = $derived.by(() => {
    if (!data) return [];
    const big = data.lifts.filter(l => l.share >= 0.04);
    const small = data.lifts.filter(l => l.share < 0.04);
    const smallSets = small.reduce((a, l) => a + l.sets, 0);
    return slices.map((_, i) => (i < big.length ? big[i].sets : smallSets));
  });

  onMount(() => {
    if (!match) location.hash = '#/';
    else {
      document.title = match;
      window.scrollTo(0, 0);
    }
  });
</script>

{#if match && data}
  <div class="wrap" id="viewMuscle">
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
    <h1 id="musTitle">{match}</h1>
    <div class="sub" id="musSub">{sub}</div>
    <div class="card">
      <MuscleVolumeChart
        id="chMusVol"
        labels={data.labels}
        counts={data.counts}
        bands={{
          mev: entry.mev !== undefined ? entry.mev : 0,
          mav: entry.mav || null,
          mrv: entry.mrv !== undefined ? entry.mrv : null,
        }}
        color={entry.color || '#888'}
      />
      <div class="cap" id="musCap">
        Weekly sets. Gold line is MEV, shaded zone is MAV, red line is MRV.
      </div>
    </div>
    <h2>Where the volume comes from</h2>
    <div class="card">
      <div class="piewrap">
        <MusclePie {slices} sets={sliceSets} />
        <div class="pielegend" id="musLegend">
          {#each slices as s, i}
            <div class="row">
              <span class="sw" style:background={piePalette(s.label)}></span>
              {#if s.link}
                <a href={s.link}>{s.label}</a>
              {:else}
                {s.label}
              {/if}
              <span class="meta">{sliceSets[i]} sets · {Math.round(s.frac * 100)}%</span>
            </div>
          {/each}
          {#if !slices.length}
            <div class="empty">nothing logged for this muscle yet</div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{/if}
