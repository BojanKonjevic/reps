<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtD, fmtV } from '../lib/format';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { vocabOf } from '../lib/vocab.svelte';
  import {
    coverageNote,
    defOf,
    eventsForMuscle,
    groupByDate,
    ruleIdOf,
    scopeOf,
    stateOn,
    weekIndexOf,
  } from '../lib/temporal';
  import { createEventSelection } from '../lib/eventSelection.svelte';
  import type { PieSlice } from '../pieChart';
  import { piePalette } from '../pieChart';
  import PageShell from '../components/PageShell.svelte';
  import MuscleVolumeChart from '../components/MuscleVolumeChart.svelte';
  import MusclePie from '../components/MusclePie.svelte';
  import EventStrip from '../components/EventStrip.svelte';
  import AsOfControl from '../components/AsOfControl.svelte';
  import ChangeDetail from '../components/ChangeDetail.svelte';
  import TrainingState from '../components/TrainingState.svelte';
  import Provenance from '../components/Provenance.svelte';

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

  const events = $derived(match ? eventsForMuscle(snap, match) : []);
  const groups = $derived(groupByDate(events));
  const markWeeks = $derived.by(() => {
    const starts = snap.volume_history.week_starts;
    const out = new Set<number>();
    for (const e of events) {
      const i = weekIndexOf(starts, e.date);
      if (i >= 0) out.add(i);
    }
    return Array.from(out).sort((a, b) => a - b);
  });
  const firstWeek = $derived.by(() => {
    if (!entry) return null;
    const i = entry.weekly.findIndex(n => n > 0);
    return i >= 0 ? snap.volume_history.week_starts[i] : null;
  });
  const coverNote = $derived(coverageNote(events, firstWeek));
  const pageScope = $derived(
    match ? { exercises: [], muscles: [match], days: [] } : { exercises: [], muscles: [], days: [] }
  );

  const sel = createEventSelection();
  let asof: string | null = $state(null);
  const selected = $derived(events.find(e => e.id === sel.selId) ?? null);
  const panelDate = $derived(sel.stateDate ?? asof);
  const panelState = $derived(panelDate ? stateOn(snap, panelDate) : null);
  const panelScope = $derived(selected && sel.stateDate ? scopeOf(selected) : pageScope);
  const panelRule = $derived(selected && sel.stateDate ? ruleIdOf(selected) : null);

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
          {markWeeks}
        />
        <div class="cap" id="musCap">
          Weekly sets. Gold line is MEV, shaded zone is MAV, red line is MRV. Ticks mark recorded
          priority and program changes.
        </div>
        {#if coverNote}
          <div class="cap" id="musHistNote">{coverNote}</div>
        {/if}
        <AsOfControl
          dates={groups.map(g => g.date)}
          value={asof}
          onPick={d => (asof = d)}
          id="musAsof"
        />
        <EventStrip {groups} selectedId={sel.selId} onSelect={sel.select} id="musEvents" />
        {#if selected}
          <ChangeDetail
            event={selected}
            events={snap.history}
            stateOpen={sel.stateDate === selected.date}
            onViewState={sel.viewState}
            id="musChange"
          />
        {/if}
        {#if panelState && panelDate}
          <TrainingState
            histState={panelState}
            {snap}
            scope={panelScope}
            ruleId={panelRule}
            id="musState"
          />
        {/if}
        <Provenance def={defOf(snap, 'muscle_volume')} id="musProv" />
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
