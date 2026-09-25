<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtD, fmtV } from '../lib/format';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { vocabOf } from '../lib/vocab.svelte';
  import type { PieSlice } from '../pieChart';
  import { piePalette } from '../pieChart';
  import PageShell from '../components/PageShell.svelte';
  import MuscleVolumeChart from '../components/MuscleVolumeChart.svelte';
  import MusclePie from '../components/MusclePie.svelte';

  interface Props {
    snap: Snapshot;
    muscle: string;
  }

  let { snap, muscle: requested }: Props = $props();

  const vocab = $derived(vocabOf(snap));
  const match = $derived(vocab.groups.filter(g => g.toLowerCase() === requested.toLowerCase())[0]);
  const entry = $derived(snap.muscles.find(m => m.muscle === match));

  const sub = $derived.by(() => {
    if (!match || !entry) return '';
    const mav = entry.bands.mav ? entry.bands.mav[0] + '-' + entry.bands.mav[1] : 'no range';
    const mrv =
      entry.bands.mrv !== undefined && entry.bands.mrv !== null ? entry.bands.mrv : 'no cap';
    const isFocus = entry.tier === 'priority';
    return (
      'MEV ' +
      entry.bands.mev +
      ' · MAV ' +
      mav +
      ' · MRV ' +
      mrv +
      ' · last 4 weeks avg ' +
      fmtV(entry.avg_recent) +
      '/wk · trained ' +
      entry.trained_weeks +
      ' of last ' +
      entry.weekly.length +
      ' weeks' +
      (isFocus ? ' · focus' : '')
    );
  });

  const slices = $derived.by((): PieSlice[] => {
    if (!entry) return [];
    const ranked = entry.lift_share;
    const big = ranked.filter(l => l.share >= 0.04);
    const small = ranked.filter(l => l.share < 0.04);
    const smallSets = small.reduce((a, l) => a + l.sets, 0);
    const total = ranked.reduce((a, l) => a + l.sets, 0);
    const out: PieSlice[] = big.map(l => ({
      label: l.exercise,
      frac: l.share,
      link: href.lift(l.exercise),
    }));
    if (smallSets > 0) {
      out.push({
        label: small.length + ' smaller lifts',
        frac: smallSets / (total || 1),
        link: null,
      });
    }
    return out;
  });

  const sliceSets = $derived.by(() => {
    if (!entry) return [];
    const big = entry.lift_share.filter(l => l.share >= 0.04);
    const small = entry.lift_share.filter(l => l.share < 0.04);
    const smallSets = small.reduce((a, l) => a + l.sets, 0);
    return slices.map((_, i) => (i < big.length ? big[i].sets : smallSets));
  });

  const labels = $derived(snap.volume_history.week_starts.map(fmtD));

  onMount(() => {
    if (!match) location.hash = href.dash();
    else {
      document.title = match;
    }
  });
</script>

{#if match && entry}
  <PageShell back>
    <div class="wrap" id="viewMuscle">
      <h1 id="musTitle">{match}</h1>
      <div class="sub" id="musSub">{sub}</div>
      <div class="card">
        <MuscleVolumeChart
          id="chMusVol"
          {labels}
          counts={entry.weekly}
          bands={{
            mev: entry.bands.mev,
            mav: entry.bands.mav,
            mrv: entry.bands.mrv,
          }}
          color={vocab.colors[match] || ''}
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
  </PageShell>
{/if}
