<script lang="ts">
  import { onMount } from 'svelte';
  import { e1rm, fmtV } from '../utils';
  import { liftColor } from '../charts';
  import { deloadWatch, isStalling } from '../forward';
  import type { Snapshot } from '../schemas/snapshot';
  import { computeTrend, musclesOf, prData, rankLifts } from '../lib/dashboard';
  import { ui } from '../lib/filters.svelte';
  import TrendMini from '../components/TrendMini.svelte';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  const top = $derived(rankLifts(snap));
  const trend = $derived(computeTrend(snap, top));
  const pr = $derived(prData(snap));

  const wdate = $derived.by(() => {
    const m: Record<number, string> = {};
    for (const w of snap.workouts) m[w.id] = w.date;
    return m;
  });

  const holds = $derived(
    (snap.autoreg?.holds || []) as Array<{
      movements?: string;
      action?: string;
      hold_until?: string;
      reason?: string;
    }>
  );
  const changes = $derived(snap.autoreg_changes);
  const prog = $derived(
    snap.progression as Record<
      string,
      { verdict?: string; next?: string; direction?: string; note?: string }
    >
  );
  const notesByEx = $derived.by(() => {
    const m: Record<string, string[]> = {};
    for (const n of snap.movement_notes) {
      const ex = String(n['exercise'] || '');
      (m[ex] = m[ex] || []).push(String(n['note'] || ''));
    }
    return m;
  });

  function heldSet(): Set<string> {
    const out = new Set<string>();
    for (const h of holds) {
      for (const m of String(h.movements || '').split('/')) {
        const t = m.trim().toLowerCase();
        if (t) out.add(t);
      }
    }
    return out;
  }

  function changedSet(): Set<string> {
    const out = new Set<string>();
    for (const ch of changes || []) {
      if (ch['reverted_on']) continue;
      for (const m of String(ch['after_movements'] || '').split('/')) {
        const t = m.trim().toLowerCase();
        if (t) out.add(t);
      }
    }
    return out;
  }

  function groupedOf(ex: string): string[] {
    const out: string[] = [];
    for (const [mus, lifts] of Object.entries(snap.autoreg?.grouped || {})) {
      if ((lifts as string[]).some(l => l.toLowerCase() === ex.toLowerCase())) out.push(mus);
    }
    return out;
  }

  function changeOf(ex: string) {
    const low = ex.toLowerCase();
    for (const ch of changes || []) {
      if (ch['reverted_on']) continue;
      const moves = String(ch['after_movements'] || '')
        .split('/')
        .map(m => m.trim().toLowerCase());
      if (moves.includes(low)) return ch;
    }
    return null;
  }

  function liftRank(t: string, i: number, held: Set<string>, changed: Set<string>): number {
    if (held.has(t.toLowerCase()) || changed.has(t.toLowerCase())) return 0;
    const pts = trend.series[i].filter((v): v is number => v !== null).map(ev => ({ ev }));
    if (isStalling(pts) || deloadWatch(pts)) return 1;
    if (snap.goals.some(g => String(g['exercise'] || '').toLowerCase() === t.toLowerCase()))
      return 2;
    return 3;
  }

  function liftPasses(t: string, i: number, held: Set<string>, changed: Set<string>): boolean {
    if (ui.liftQ && !t.toLowerCase().includes(ui.liftQ)) return false;
    if (!ui.liftFacets.size) return true;
    for (const f of ui.liftFacets) {
      if (f === 'autoreg' && (held.has(t.toLowerCase()) || changed.has(t.toLowerCase())))
        return true;
      if (f === 'grouped' && groupedOf(t).length) return true;
      if (
        f === 'goal' &&
        snap.goals.some(g => String(g['exercise'] || '').toLowerCase() === t.toLowerCase())
      )
        return true;
      if (f === 'stall') {
        const pts = trend.series[i].filter((v): v is number => v !== null).map(ev => ({ ev }));
        if (isStalling(pts) || deloadWatch(pts)) return true;
      }
      if (f === 'focus') {
        const prio = snap.priority;
        const has = musclesOf(snap, t).some(m => {
          const e = prio[m] as string | { tier?: string } | undefined;
          return (typeof e === 'string' ? e : e?.tier) === 'priority';
        });
        if (has) return true;
      }
    }
    return false;
  }

  const order = $derived.by(() => {
    const held = heldSet();
    const changed = changedSet();
    return top
      .map((t, i) => i)
      .sort(
        (a, b) =>
          liftRank(top[a], a, held, changed) - liftRank(top[b], b, held, changed) ||
          (top[a] < top[b] ? -1 : 1)
      )
      .filter(i => liftPasses(top[i], i, held, changed));
  });

  const thisMonth = new Date().toISOString().slice(0, 7);
  const prThisMonth = $derived.by(() => {
    const m: Record<string, boolean> = {};
    for (const s of snap.sets) {
      if (pr.prIds.has(s.id) && (wdate[s.workout_id] || '').slice(0, 7) === thisMonth)
        m[s.exercise] = true;
    }
    return m;
  });

  interface Mark {
    text: string;
    cls: string;
  }

  function marksFor(t: string, vals: Array<number | null>): Mark[] {
    const marks: Mark[] = [];
    holds
      .filter(hh =>
        String(hh.movements || '')
          .split('/')
          .some(m => m.trim().toLowerCase() === t.toLowerCase())
      )
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
        text:
          'adjusted ' + String(change['date']) + ': ' + (change['evidence'] || change['action']),
        cls: 'plan',
      });
    const grouped = groupedOf(t);
    if (grouped.length) marks.push({ text: 'grouped fatigue: ' + grouped.join(', '), cls: 'bad' });
    const pts = vals.filter((v): v is number => v !== null).map(ev => ({ ev }));
    if (isStalling(pts)) marks.push({ text: 'stalling', cls: 'bad' });
    else if (deloadWatch(pts)) marks.push({ text: 'slipping', cls: 'bad' });
    if (snap.goals.some(g => String(g['exercise'] || '').toLowerCase() === t.toLowerCase()))
      marks.push({ text: 'goal', cls: 'plan' });
    return marks;
  }

  function lastBest(t: string): string | null {
    const sets = snap.sets.filter(s => s.exercise === t);
    if (!sets.length) return null;
    const last = sets.slice().sort((a, b) => {
      const d = (wdate[b.workout_id] || '').localeCompare(wdate[a.workout_id] || '');
      return d !== 0 ? d : b.id - a.id;
    })[0];
    const best = sets.slice().sort((a, b) => e1rm(b.weight, b.reps) - e1rm(a.weight, a.reps))[0];
    return (
      'last ' +
      last.weight +
      ' x ' +
      last.reps +
      ' · best ' +
      best.weight +
      ' x ' +
      best.reps +
      ' (e1RM ' +
      fmtV(e1rm(best.weight, best.reps)) +
      ')'
    );
  }

  const arrows: Record<string, [string, string]> = {
    up: ['↑', '#7fd67f'],
    flat: ['→', '#b0aca2'],
    down: ['↓', '#f09090'],
  };

  onMount(() => {
    document.title = 'movements';
    window.scrollTo(0, 0);
  });
</script>

<div class="wrap" id="viewLifts">
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
        {#each [['Autoreg', 'autoreg'], ['Grouped', 'grouped'], ['Goals', 'goal'], ['Stalling', 'stall'], ['Focus', 'focus']] as [label, facet]}
          <button
            type="button"
            class="chip mini"
            class:off={!ui.liftFacets.has(facet)}
            data-facet={facet}
            aria-pressed={ui.liftFacets.has(facet)}
            onclick={() => {
              if (ui.liftFacets.has(facet)) ui.liftFacets.delete(facet);
              else ui.liftFacets.add(facet);
            }}>{label}</button
          >
        {/each}
      </span>
    </div>
    <div class="listgrid" id="liftGrid">
      {#each order as i}
        {@const t = top[i]}
        {@const vals = trend.series[i]}
        {@const marks = marksFor(t, vals)}
        {@const mus = musclesOf(snap, t)}
        {@const lb = lastBest(t)}
        {@const p = prog[t.toLowerCase()]}
        <div
          class="card"
          style="margin: 0"
          role="link"
          tabindex="0"
          onclick={ev => {
            if ((ev.target as HTMLElement).tagName !== 'A')
              location.hash = '#/l/' + encodeURIComponent(t);
          }}
          onkeydown={ev => {
            if (ev.key === 'Enter') location.hash = '#/l/' + encodeURIComponent(t);
          }}
        >
          <div class="listrow">
            <div class="listinfo">
              <div class="minititle">
                <a href="#/l/{encodeURIComponent(t)}">{t}</a>
                {#if prThisMonth[t]}<span class="prt" title="PR'd this month"
                    ><svg viewBox="0 0 16 16"
                      ><path d="M5 1.5h6v4.2a3 3 0 0 1-6 0V1.5z" fill="currentColor" /><path
                        d="M5 2.5H3.2a2.8 2.8 0 0 0 2.9 3.6M11 2.5h1.8a2.8 2.8 0 0 1-2.9 3.6"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.4"
                      /><path
                        d="M8 8.7v2.1M6.2 12.8h3.6M5.4 14.5h5.2"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.4"
                        stroke-linecap="round"
                      /></svg
                    ></span
                  >{/if}
                {#if marks.length}
                  <span class="ministat">
                    {#each marks as m}
                      <span class="minisub {m.cls}">{m.text}</span>
                    {/each}
                  </span>
                {/if}
              </div>
              {#if mus.length}
                <div class="legend">
                  {#each mus as m}
                    <a class="chip" href="#/m/{encodeURIComponent(m)}">{m}</a>
                  {/each}
                </div>
              {/if}
              {#if lb}<div class="cap">{lb}</div>{/if}
              {#if p}
                <div class="cap">
                  {p.verdict}
                  {#if p.direction && arrows[p.direction]}
                    <span style:color={arrows[p.direction][1]} style:font-weight="700"
                      >{arrows[p.direction][0]}</span
                    >
                    {' ' + p.next + (p.note ? ' · ' + p.note : '')}
                  {:else}
                    → {p.next}{p.note ? ' · ' + p.note : ''}
                  {/if}
                </div>
              {/if}
              {#each notesByEx[t] || [] as n}
                <div class="cap">setup: {n}</div>
              {/each}
            </div>
            <div class="listchart">
              <a
                href="#/l/{encodeURIComponent(t)}"
                aria-label={t}
                style="display:block; width: 100%"
              >
                <TrendMini days={trend.days} {vals} color={liftColor(t)} />
              </a>
            </div>
          </div>
        </div>
      {/each}
    </div>
    <div class="cap">Tap a lift for PR history, trajectory, and full history.</div>
  </div>
</div>
