<script lang="ts">
  import { onMount } from 'svelte';
  import { fmtD, fmtLong } from '../lib/format';
  import { href } from '../routes';
  import type { Snapshot } from '../generated/snapshot';
  import { liftByName } from '../lib/select';
  import Icon from '../components/Icon.svelte';

  interface Props {
    snap: Snapshot;
    date: string;
  }

  let { snap, date: ds }: Props = $props();

  const dates = $derived(Array.from(new Set(snap.sessions.map(s => s.date))).sort());
  const ix = $derived(dates.indexOf(ds));
  const prev = $derived(ix > 0 ? dates[ix - 1] : null);
  const next = $derived(ix >= 0 && ix < dates.length - 1 ? dates[ix + 1] : null);

  const day = $derived(snap.sessions.filter(s => s.date === ds));
  const wnotes = $derived(day.map(s => s.notes).filter(n => n));
  const allRest = $derived(day.length > 0 && day.every(s => s.status === 'rest'));

  interface ExBlock {
    ex: string;
    prog: string | null;
    rows: Array<{ n: number; detail: string; ev: string; pr: boolean }>;
    notes: Array<{ ex: string; n: number; note: string }>;
  }

  const blocks = $derived.by((): ExBlock[] => {
    const out: ExBlock[] = [];
    for (const sess of day) {
      for (const group of sess.exercises) {
        const ex = group.exercise;
        const lift = liftByName(snap.lifts, ex);
        const subs: string[] = [];
        if (lift?.progression)
          subs.push(lift.progression.verdict + ', next ' + lift.progression.next);
        if (group.deload) subs.push('deload');
        const rows = group.sets.map(s => ({
          n: s.n,
          detail: s.w + ' x ' + s.r,
          ev: s.e.toFixed(1),
          pr: s.pr,
        }));
        const notes = group.sets.map(s => ({ ex, n: s.n, note: s.note })).filter(r => r.note);
        out.push({ ex, prog: subs.length ? subs.join(' · ') : null, rows, notes });
      }
    }
    return out;
  });

  const title = $derived(
    !day.length ? fmtD(ds) : fmtLong(ds) + (day[0].slot_label ? ', ' + day[0].slot_label : '')
  );

  onMount(() => {
    document.title = fmtD(ds) + (!day.length ? ' no session' : allRest ? ' rest day' : ' training');
  });
</script>

<div id="viewSession">
  <div class="sessnav">
    <a href={href.dash()}>← session</a>
    <span class="sesspg">
      {#if prev}
        <a
          class="iconbtn"
          id="sessPrev"
          href={href.session(prev)}
          aria-label="previous session {fmtD(prev)}"><Icon name="chevronLeft" /></a
        >
      {:else}
        <span class="iconbtn" id="sessPrev" aria-hidden="true" style="visibility: hidden"
          ><Icon name="chevronLeft" /></span
        >
      {/if}
      {#if next}
        <a
          class="iconbtn"
          id="sessNext"
          href={href.session(next)}
          aria-label="next session {fmtD(next)}"><Icon name="chevronRight" /></a
        >
      {:else}
        <span class="iconbtn" id="sessNext" aria-hidden="true" style="visibility: hidden"
          ><Icon name="chevronRight" /></span
        >
      {/if}
    </span>
  </div>
  <h1 id="sessTitle">{title}</h1>
  <div id="sessNotes">
    {#if allRest}
      <div class="restday">rest day</div>
    {/if}
    {#if wnotes.length}
      <div class="sessnotes">{wnotes.join(' / ')}</div>
    {/if}
  </div>
  <div id="sessBody" class="exgrid">
    {#if !day.length}
      <div class="empty">no session logged this day</div>
    {/if}
    {#each blocks as b}
      <section class="exblock ex">
        <h3>
          <a href={href.lift(b.ex)}>{b.ex}</a>
          {#if b.prog}<span class="exsub">{b.prog}</span>{/if}
        </h3>
        <table class="sess">
          <thead>
            <tr>
              <th scope="col">set</th>
              <th scope="col">weight × reps</th>
              <th scope="col" class="num">e1RM</th>
            </tr>
          </thead>
          <tbody>
            {#each b.rows as r}
              <tr>
                <td class="setnum">{r.n}</td>
                <td>
                  {r.detail}
                  {#if r.pr}<span class="prbadge" title="personal record"
                      ><Icon name="trophy" size={13} /></span
                    >{/if}
                </td>
                <td class="num">{r.ev}</td>
              </tr>
            {/each}
          </tbody>
        </table>
        {#if b.notes.length}
          <div class="setnotes">
            {#each b.notes as n}
              <div><b>{n.ex} {n.n}</b>{n.note}</div>
            {/each}
          </div>
        {/if}
      </section>
    {/each}
  </div>
</div>

<style>
  .sessnav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    font-size: 12.5px;
    color: var(--ink-mute);
  }
  .sessnav a:hover {
    color: var(--ink);
  }
  .sessnotes {
    font-size: 13px;
    color: var(--ink-dim);
    margin-top: 8px;
  }
</style>
