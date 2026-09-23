<script lang="ts">
  import { onMount } from 'svelte';
  import { e1rm, fmtD } from '../utils';
  import type { Snapshot } from '../schemas/snapshot';
  import { prData, slotOfDate } from '../lib/dashboard';

  interface Props {
    snap: Snapshot;
    date: string;
  }

  let { snap, date: ds }: Props = $props();

  const pr = $derived(prData(snap));
  const slots = $derived(slotOfDate(snap));

  const dates = $derived(Array.from(new Set(snap.workouts.map(w => w.date))).sort());
  const ix = $derived(dates.indexOf(ds));
  const prev = $derived(ix > 0 ? dates[ix - 1] : null);
  const next = $derived(ix >= 0 && ix < dates.length - 1 ? dates[ix + 1] : null);

  const ws = $derived(snap.workouts.filter(w => w.date === ds));
  const wnotes = $derived(ws.map(w => w.notes).filter(n => n));
  const allRest = $derived(ws.length > 0 && ws.every(w => w.status === 'rest'));

  interface ExBlock {
    ex: string;
    prog: string | null;
    rows: Array<{ n: number; detail: string; ev: string; pr: boolean }>;
    notes: Array<{ ex: string; n: number; note: string }>;
  }

  const blocks = $derived.by((): ExBlock[] => {
    const out: ExBlock[] = [];
    ws.forEach(w => {
      const sets = snap.sets.filter(s => s.workout_id === w.id);
      const order: string[] = [];
      const byEx: Record<string, typeof sets> = {};
      sets.forEach(s => {
        (byEx[s.exercise] = byEx[s.exercise] || []).push(s);
        if (!order.includes(s.exercise)) order.push(s.exercise);
      });
      order.forEach(ex => {
        const progEntry = snap.progression[ex.toLowerCase()] as
          { verdict?: string; next?: string } | undefined;
        const subs: string[] = [];
        if (progEntry) subs.push(progEntry.verdict + ', next ' + progEntry.next);
        const deload = snap.deload || [];
        if (
          deload.some(
            d =>
              (d['scope'] === 'lift' &&
                String(d['subject'] || '').toLowerCase() === ex.toLowerCase()) ||
              (d['scope'] === 'slot' && d['subject'] === slots[ds])
          )
        ) {
          subs.push('deload');
        }
        const rows = byEx[ex].map((s, i) => ({
          n: i + 1,
          detail: s.weight + ' x ' + s.reps,
          ev: e1rm(s.weight, s.reps).toFixed(1),
          pr: pr.prIds.has(s.id),
        }));
        const notes = byEx[ex].map((s, i) => ({ ex, n: i + 1, note: s.note })).filter(r => r.note);
        out.push({ ex, prog: subs.length ? subs.join(' · ') : null, rows, notes });
      });
    });
    return out;
  });

  const title = $derived(
    !ws.length
      ? fmtD(ds)
      : new Date(ds + 'T12:00:00').toLocaleDateString(undefined, {
          weekday: 'long',
          month: 'long',
          day: 'numeric',
        }) + (slots[ds] ? ', ' + slots[ds] : '')
  );

  onMount(() => {
    document.title = fmtD(ds) + (!ws.length ? ' no session' : allRest ? ' rest day' : ' training');
    window.scrollTo(0, 0);
  });
</script>

<div class="wrap" id="viewSession">
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
    <span class="sesspg">
      {#if prev}
        <a
          class="iconbtn"
          id="sessPrev"
          href="#/s/{prev}"
          aria-label="previous session {fmtD(prev)}"
          ><svg viewBox="0 0 16 16" width="22" height="22">
            <path
              d="M10 3 L5 8 L10 13"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            /></svg
          ></a
        >
      {:else}
        <a
          class="iconbtn"
          id="sessPrev"
          href="#/"
          aria-label="previous session"
          style="visibility: hidden"
          ><svg viewBox="0 0 16 16" width="22" height="22">
            <path
              d="M10 3 L5 8 L10 13"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            /></svg
          ></a
        >
      {/if}
      {#if next}
        <a class="iconbtn" id="sessNext" href="#/s/{next}" aria-label="next session {fmtD(next)}"
          ><svg viewBox="0 0 16 16" width="22" height="22">
            <path
              d="M6 3 L11 8 L6 13"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            /></svg
          ></a
        >
      {:else}
        <a
          class="iconbtn"
          id="sessNext"
          href="#/"
          aria-label="next session"
          style="visibility: hidden"
          ><svg viewBox="0 0 16 16" width="22" height="22">
            <path
              d="M6 3 L11 8 L6 13"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
              stroke-linecap="round"
              stroke-linejoin="round"
            /></svg
          ></a
        >
      {/if}
    </span>
  </div>
  <h1 id="sessTitle">{title}</h1>
  <div id="sessNotes">
    {#if allRest}
      <div class="card restday">rest day</div>
    {/if}
    {#if wnotes.length}
      <div class="card">{wnotes.join(' / ')}</div>
    {/if}
    {#each blocks as b}
      {#if b.notes.length}
        <div class="setnotes">
          {#each b.notes as n}
            <div><b>{n.ex} {n.n}</b>{n.note}</div>
          {/each}
        </div>
      {/if}
    {/each}
  </div>
  <div id="sessBody" class="exgrid">
    {#each blocks as b}
      <div class="card ex">
        <h3>
          <a href="#/l/{encodeURIComponent(b.ex)}">{b.ex}</a>
          {#if b.prog}<span class="exsub">{b.prog}</span>{/if}
        </h3>
        <table class="sess">
          <thead>
            <tr><th scope="col">set</th><th scope="col">weight</th><th scope="col">e1RM</th></tr>
          </thead>
          <tbody>
            {#each b.rows as r}
              <tr>
                <td>{r.n}</td>
                <td>
                  {r.detail}
                  {#if r.pr}<span class="prbadge" title="personal record"
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
                </td>
                <td>{r.ev}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/each}
  </div>
</div>
