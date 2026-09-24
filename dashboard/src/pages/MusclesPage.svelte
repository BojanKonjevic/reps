<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtD } from '../lib/format';
  import { statusLabel } from '../lib/present';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { ui } from '../lib/filters.svelte';
  import { vocabOf } from '../lib/vocab.svelte';
  import PageShell from '../components/PageShell.svelte';
  import FacetChips from '../components/FacetChips.svelte';
  import MuscleVolumeChart from '../components/MuscleVolumeChart.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const vocab = $derived(vocabOf(snap));
  const grouped = $derived(snap.autoreg?.grouped ?? {});

  function tierOf(m: string): string {
    return snap.muscles.find(x => x.muscle === m)?.tier ?? 'maintain';
  }

  function bad(m: string): boolean {
    const v = snap.muscles.find(x => x.muscle === m);
    return !!v && (v.status === 'below_mev' || v.status === 'above_mrv');
  }

  function musPasses(m: string): boolean {
    if (!ui.muscleFacets.size) return true;
    const v = snap.muscles.find(x => x.muscle === m);
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
    vocab.groups.slice().sort((a, b) => {
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

  const wlabels = $derived(snap.volume_history.week_starts.map(fmtD));

  interface Mark {
    text: string;
    cls: string;
  }

  function marksFor(m: string): Mark[] {
    const marks: Mark[] = [];
    const entry = snap.muscles.find(x => x.muscle === m);
    if (entry) {
      if (entry.status === 'below_mev') marks.push({ text: 'below MEV', cls: 'bad' });
      else if (entry.status === 'above_mrv') marks.push({ text: 'above MRV', cls: 'bad' });
      else marks.push({ text: statusLabel(entry.status), cls: '' });
    }
    const tier = tierOf(m);
    if (tier && tier !== 'maintain')
      marks.push({ text: tier, cls: tier === 'priority' ? 'plan' : '' });
    if (grouped[m]) marks.push({ text: 'grouped fatigue: ' + grouped[m].join(', '), cls: 'bad' });
    return marks;
  }

  function toggleFacet(f: string) {
    if (ui.muscleFacets.has(f)) ui.muscleFacets.delete(f);
    else ui.muscleFacets.add(f);
  }

  onMount(() => {
    document.title = 'muscles';
    window.scrollTo(0, 0);
  });
</script>

<PageShell back>
  <div class="wrap" id="viewMuscles">
    <h1>Muscles</h1>
    <div class="sub" id="musSub2">{shown.length} muscles</div>
    <div class="card">
      <div class="filterbar">
        <span class="legend" id="musFacets">
          <FacetChips
            facets={[
              ['Below MEV', 'below'],
              ['Above MRV', 'above'],
              ['Priority', 'priority'],
              ['Grouped', 'grouped'],
            ]}
            active={ui.muscleFacets}
            onToggle={toggleFacet}
          />
        </span>
      </div>
      <div class="listgrid" id="musGrid">
        {#each shown as m}
          {@const entry = snap.muscles.find(x => x.muscle === m)}
          {@const lifts = entry?.lift_share ?? []}
          <div
            class="card"
            style="margin: 0"
            role="link"
            tabindex="0"
            onclick={ev => {
              if ((ev.target as HTMLElement).tagName !== 'A') location.hash = href.muscle(m);
            }}
            onkeydown={ev => {
              if (ev.key === 'Enter') location.hash = href.muscle(m);
            }}
          >
            <div class="listrow">
              <div class="listinfo">
                <div class="minititle">
                  <a href={href.muscle(m)}>{m}</a>
                  <span class="ministat">
                    {#each marksFor(m) as x}
                      <span class={'minisub ' + x.cls}>{x.text}</span>
                    {/each}
                  </span>
                </div>
                {#each lifts.slice(0, 3) as l}
                  <div class="cap">
                    <a href={href.lift(l.exercise)}>{l.exercise}</a>
                    <span> {l.sets} sets · {Math.round(l.share * 100)}%</span>
                  </div>
                {/each}
                {#if lifts.length > 3}
                  <div class="cap">
                    <a href={href.muscle(m)}>+{lifts.length - 3} more</a>
                  </div>
                {/if}
              </div>
              <div class="listchart">
                <MuscleVolumeChart
                  labels={wlabels}
                  counts={entry?.weekly ?? []}
                  bands={{
                    mev: entry?.bands.mev ?? 0,
                    mav: entry?.bands.mav ?? null,
                    mrv: entry?.bands.mrv ?? null,
                  }}
                  color={vocab.colors[m] || ''}
                />
              </div>
            </div>
          </div>
        {/each}
      </div>
      <div class="cap">Weekly sets against MEV/MAV/MRV. Tap a muscle for the full page.</div>
    </div>
  </div>
</PageShell>
