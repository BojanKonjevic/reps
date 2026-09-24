<script lang="ts">
  import { onMount } from 'svelte';
  import { directionArrow, directionClass, markText, markClass } from '../lib/present';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { trendMatrix, liftByName } from '../lib/select';
  import { vocabOf } from '../lib/vocab.svelte';
  import { ui } from '../lib/filters.svelte';
  import PageShell from '../components/PageShell.svelte';
  import FacetChips from '../components/FacetChips.svelte';
  import Icon from '../components/Icon.svelte';
  import TrendMini from '../components/TrendMini.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const vocab = $derived(vocabOf(snap));
  const matrix = $derived(trendMatrix(snap.lifts));

  const holds = $derived(snap.autoreg?.holds ?? []);
  const changes = $derived(snap.autoreg_changes);

  function heldSet(): Set<string> {
    const out = new Set<string>();
    for (const h of holds) {
      for (const m of h.movements.split('/')) {
        const t = m.trim().toLowerCase();
        if (t) out.add(t);
      }
    }
    return out;
  }

  function changedSet(): Set<string> {
    const out = new Set<string>();
    for (const ch of changes) {
      if (ch.reverted_on) continue;
      for (const m of ch.after_movements.split('/')) {
        const t = m.trim().toLowerCase();
        if (t) out.add(t);
      }
    }
    return out;
  }

  function groupedOf(ex: string): string[] {
    const out: string[] = [];
    for (const [mus, lifts] of Object.entries(snap.autoreg?.grouped || {})) {
      if (lifts.some(l => l.toLowerCase() === ex.toLowerCase())) out.push(mus);
    }
    return out;
  }

  function changeOf(ex: string) {
    const low = ex.toLowerCase();
    for (const ch of changes) {
      if (ch.reverted_on) continue;
      const moves = ch.after_movements.split('/').map(m => m.trim().toLowerCase());
      if (moves.includes(low)) return ch;
    }
    return null;
  }

  function liftRank(t: string, held: Set<string>, changed: Set<string>): number {
    if (held.has(t.toLowerCase()) || changed.has(t.toLowerCase())) return 0;
    const lift = liftByName(snap.lifts, t);
    const tags = new Set(lift?.tags ?? []);
    if (tags.has('stalling') || tags.has('slipping')) return 1;
    if (tags.has('goal')) return 2;
    return 3;
  }

  function liftPasses(t: string, held: Set<string>, changed: Set<string>): boolean {
    if (ui.liftQ && !t.toLowerCase().includes(ui.liftQ)) return false;
    if (!ui.liftFacets.size) return true;
    const lift = liftByName(snap.lifts, t);
    const tags = new Set(lift?.tags ?? []);
    for (const f of ui.liftFacets) {
      if (f === 'autoreg' && (held.has(t.toLowerCase()) || changed.has(t.toLowerCase())))
        return true;
      if (f === 'grouped' && groupedOf(t).length) return true;
      if (f === 'goal' && tags.has('goal')) return true;
      if (f === 'stall' && (tags.has('stalling') || tags.has('slipping'))) return true;
      if (f === 'focus' && tags.has('focus')) return true;
    }
    return false;
  }

  const order = $derived.by(() => {
    const held = heldSet();
    const changed = changedSet();
    return snap.lifts
      .slice()
      .sort(
        (a, b) =>
          liftRank(a.exercise, held, changed) - liftRank(b.exercise, held, changed) ||
          (a.exercise < b.exercise ? -1 : 1)
      )
      .filter(l => liftPasses(l.exercise, held, changed));
  });

  const asOfMonth = $derived(snap.as_of.slice(0, 7));
  const prThisMonth = $derived.by(() => {
    const m: Record<string, boolean> = {};
    for (const l of snap.lifts) {
      if (l.sessions.some(s => s.is_pr && s.date.slice(0, 7) === asOfMonth)) m[l.exercise] = true;
    }
    return m;
  });

  interface Mark {
    text: string;
    cls: string;
  }

  function marksFor(t: string): Mark[] {
    const marks: Mark[] = [];
    holds
      .filter(hh => hh.movements.split('/').some(m => m.trim().toLowerCase() === t.toLowerCase()))
      .forEach(hh =>
        marks.push({
          text:
            hh.action +
            ', holds until ' +
            hh.hold_until +
            (hh.reason ? ' (' + hh.reason + ')' : ''),
          cls: 'bad',
        })
      );
    const change = changeOf(t);
    if (change)
      marks.push({
        text: 'adjusted ' + change.date + ': ' + (change.evidence || change.action),
        cls: 'plan',
      });
    const grouped = groupedOf(t);
    if (grouped.length) marks.push({ text: 'grouped fatigue: ' + grouped.join(', '), cls: 'bad' });
    const lift = liftByName(snap.lifts, t);
    for (const mk of lift?.marks ?? []) {
      if (mk.kind === 'stalling' || mk.kind === 'slipping' || mk.kind === 'goal')
        marks.push({ text: markText(mk.kind), cls: markClass(mk.kind) });
    }
    return marks;
  }

  function lastBest(t: string): string | null {
    const lift = liftByName(snap.lifts, t);
    if (!lift || !lift.last || !lift.best) return null;
    return (
      'last ' +
      lift.last.weight +
      ' x ' +
      lift.last.reps +
      ' · best ' +
      lift.best.weight +
      ' x ' +
      lift.best.reps +
      ' (e1RM ' +
      lift.best.e1rm.toFixed(1) +
      ')'
    );
  }

  function toggleFacet(f: string) {
    if (ui.liftFacets.has(f)) ui.liftFacets.delete(f);
    else ui.liftFacets.add(f);
  }

  onMount(() => {
    document.title = 'movements';
    window.scrollTo(0, 0);
  });
</script>

<PageShell back>
  <div class="wrap" id="viewLifts">
    <h1>Movements</h1>
    <div class="sub" id="liftsSub">{order.length} movements</div>
    <div class="card">
      <div class="filterbar">
        <input
          id="liftSearch"
          type="search"
          placeholder="search lifts"
          aria-label="search lifts"
          value={ui.liftQ}
          oninput={e => {
            ui.liftQ = (e.target as HTMLInputElement).value.trim().toLowerCase();
          }}
        />
        <span class="legend" id="liftFacets">
          <FacetChips
            facets={[
              ['Autoreg', 'autoreg'],
              ['Grouped', 'grouped'],
              ['Goals', 'goal'],
              ['Stalling', 'stall'],
              ['Focus', 'focus'],
            ]}
            active={ui.liftFacets}
            onToggle={toggleFacet}
          />
        </span>
      </div>
      <div class="listgrid" id="liftGrid">
        {#each order as lift}
          {@const idx = matrix.top.indexOf(lift.exercise)}
          {@const vals = matrix.series[idx]}
          {@const marks = marksFor(lift.exercise)}
          {@const lb = lastBest(lift.exercise)}
          {@const p = lift.progression}
          <div
            class="card"
            style="margin: 0"
            role="link"
            tabindex="0"
            onclick={ev => {
              if ((ev.target as HTMLElement).tagName !== 'A')
                location.hash = href.lift(lift.exercise);
            }}
            onkeydown={ev => {
              if (ev.key === 'Enter') location.hash = href.lift(lift.exercise);
            }}
          >
            <div class="listrow">
              <div class="listinfo">
                <div class="minititle">
                  <a href={href.lift(lift.exercise)}>{lift.exercise}</a>
                  {#if prThisMonth[lift.exercise]}<span class="prt" title="PR'd this month"
                      ><Icon name="trophy" size={14} /></span
                    >{/if}
                  {#if marks.length}
                    <span class="ministat">
                      {#each marks as m}
                        <span class="minisub {m.cls}">{m.text}</span>
                      {/each}
                    </span>
                  {/if}
                </div>
                {#if lift.muscles.length}
                  <div class="legend">
                    {#each lift.muscles as m}
                      <a class="chip" href={href.muscle(m)}>{m}</a>
                    {/each}
                  </div>
                {/if}
                {#if lb}<div class="cap">{lb}</div>{/if}
                {#if p}
                  <div class="cap">
                    {p.verdict}
                    <span class={directionClass(p.direction)} style:font-weight="700"
                      >{directionArrow(p.direction)}</span
                    >
                    {' ' + p.next + (p.note ? ' · ' + p.note : '')}
                  </div>
                {/if}
                {#each lift.notes as n}
                  <div class="cap">setup: {n}</div>
                {/each}
              </div>
              <div class="listchart">
                <a
                  href={href.lift(lift.exercise)}
                  aria-label={lift.exercise}
                  style="display:block; width: 100%"
                >
                  <TrendMini
                    {lift}
                    days={matrix.days}
                    {vals}
                    color={vocab.liftColor(lift.exercise)}
                  />
                </a>
              </div>
            </div>
          </div>
        {/each}
      </div>
      <div class="cap">Tap a lift for PR history, trajectory, and full history.</div>
    </div>
  </div>
</PageShell>
