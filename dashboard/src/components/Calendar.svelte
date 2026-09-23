<script lang="ts">
  import { hideTip, showTip } from '../tip';
  import type { Snapshot } from '../schemas/snapshot';

  interface Props {
    snap: Snapshot;
    prDates: Set<string>;
    prIds: Set<number>;
    slotOfDate: Record<string, string>;
    dayDetail: Record<string, string[]>;
    restDates: Record<string, boolean>;
    missed: Record<string, string>;
    breakDays: number;
  }

  let { snap, prDates, prIds, slotOfDate, dayDetail, restDates, missed, breakDays }: Props =
    $props();

  const MONTHS = [
    'January',
    'February',
    'March',
    'April',
    'May',
    'June',
    'July',
    'August',
    'September',
    'October',
    'November',
    'December',
  ];

  const lastW = $derived(
    snap.workouts.length
      ? snap.workouts
          .map(w => w.date)
          .sort()
          .pop()!
      : new Date().toISOString().slice(0, 10)
  );
  let viewY = $state(0);
  let viewM = $state(0);
  let init = $state(false);
  $effect(() => {
    if (!init) {
      viewY = parseInt(lastW.slice(0, 4), 10);
      viewM = parseInt(lastW.slice(5, 7), 10) - 1;
      init = true;
    }
  });

  const todayS = new Date().toISOString().slice(0, 10);

  interface Cell {
    key: string;
    day: number;
    cls: string;
    link: boolean;
    title: string;
    pr: boolean;
  }

  const wByDate = $derived.by(() => {
    const m: Record<string, typeof snap.workouts> = {};
    for (const w of snap.workouts) (m[w.date] = m[w.date] || []).push(w);
    return m;
  });

  const sByDate = $derived.by(() => {
    const wid2date: Record<number, string> = {};
    for (const w of snap.workouts) wid2date[w.id] = w.date;
    const m: Record<string, typeof snap.sets> = {};
    for (const s of snap.sets) {
      const d = wid2date[s.workout_id] || s.created.slice(0, 10);
      (m[d] = m[d] || []).push(s);
    }
    return m;
  });

  const breakDates = $derived.by(() => {
    const trainedDates = Object.keys(sByDate).sort();
    const out: Record<string, boolean> = {};
    for (let i = 1; i < trainedDates.length; i += 1) {
      const gap = Math.round(
        (new Date(trainedDates[i] + 'T12:00:00').getTime() -
          new Date(trainedDates[i - 1] + 'T12:00:00').getTime()) /
          86400000
      );
      if (gap >= breakDays) out[trainedDates[i]] = true;
    }
    return out;
  });

  const cells = $derived.by((): Array<Cell | null> => {
    const first = new Date(viewY, viewM, 1);
    let lead = first.getDay() - 1;
    if (lead < 0) lead = 6;
    const out: Array<Cell | null> = [];
    for (let i = 0; i < lead; i += 1) out.push(null);
    const days = new Date(viewY, viewM + 1, 0).getDate();
    for (let d = 1; d <= days; d += 1) {
      const key =
        viewY + '-' + String(viewM + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      const trained = !!(dayDetail[key] && dayDetail[key].length > 0);
      const rested = !trained && !!restDates[key];
      const isMissed = !trained && !rested && !!missed[key] && key <= todayS;
      out.push({
        key,
        day: d,
        cls:
          'cd' +
          (trained ? ' t' : '') +
          (rested ? ' r' : '') +
          (isMissed ? ' m' : '') +
          (key === todayS ? ' today' : '') +
          (key > todayS ? ' fut' : '') +
          (breakDates[key] ? ' brk' : ''),
        link: trained || rested,
        title: isMissed ? 'missed: expected ' + missed[key] : '',
        pr: prDates.has(key),
      });
    }
    return out;
  });

  function prev() {
    hideTip();
    viewM -= 1;
    if (viewM < 0) {
      viewM = 11;
      viewY -= 1;
    }
  }

  function next() {
    hideTip();
    viewM += 1;
    if (viewM > 11) {
      viewM = 0;
      viewY += 1;
    }
  }

  function hoverDay(key: string, isPR: boolean, ev: MouseEvent) {
    hideTip();
    const sets = sByDate[key] || [];
    const order: string[] = [];
    const byEx: Record<string, typeof sets> = {};
    sets.forEach(s => {
      (byEx[s.exercise] = byEx[s.exercise] || []).push(s);
      if (!order.includes(s.exercise)) order.push(s.exercise);
    });
    const rows: Array<[string | null, string]> = [];
    order.slice(0, 6).forEach(ex => {
      const g = byEx[ex];
      const top = g.slice().sort((a, b) => b.weight - a.weight || b.reps - a.reps)[0];
      const hasPR = g.some(s => prIds.has(s.id));
      rows.push([
        hasPR ? '#e6c400' : null,
        ex + ' ' + g.length + ' x ' + top.weight + 'x' + top.reps + (hasPR ? ' PR' : ''),
      ]);
    });
    if (order.length > 6) rows.push([null, '+' + (order.length - 6) + ' more lifts']);
    const wnotes = (wByDate[key] || []).map(w => w.notes).filter(n => n);
    if (wnotes.length && rows.length < 7) {
      const n = wnotes.join(' / ');
      rows.push([null, n.length > 90 ? n.slice(0, 90) + '...' : n]);
    }
    const title =
      new Date(key + 'T12:00:00').toLocaleDateString(undefined, {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
      }) +
      (slotOfDate[key] ? ' ' + slotOfDate[key] : '') +
      (isPR ? '  PR' : '');
    showTip(title, rows.length ? rows : [[null, 'tap to open']], ev.clientX, ev.clientY);
  }
</script>

<div class="calhead">
  <button id="calPrev" type="button" aria-label="Previous month" onclick={prev}>
    <svg viewBox="0 0 16 16" width="18" height="18">
      <path
        d="M10 3 L5 8 L10 13"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </button>
  <b id="calTitle">{MONTHS[viewM]} {viewY}</b>
  <button id="calNext" type="button" aria-label="Next month" onclick={next}>
    <svg viewBox="0 0 16 16" width="18" height="18">
      <path
        d="M6 3 L11 8 L6 13"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </svg>
  </button>
</div>
<div class="cal" id="cal">
  {#each ['M', 'T', 'W', 'T', 'F', 'S', 'S'] as d}
    <div class="dw">{d}</div>
  {/each}
  {#each cells as c}
    {#if c === null}
      <div></div>
    {:else if c.link}
      <a
        href="#/s/{c.key}"
        class={c.cls}
        title={c.title || undefined}
        onmousemove={ev => hoverDay(c.key, c.pr, ev)}
        onmouseleave={hideTip}
        onclick={hideTip}
        >{c.day}{#if c.pr}<span class="prt" title="personal record"
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
          >{/if}</a
      >
    {:else}
      <div class={c.cls} title={c.title || undefined}>{c.day}</div>
    {/if}
  {/each}
</div>
<div class="cap">Tap a highlighted day for the session. Trophy marks a PR day.</div>
<div class="cap">Recent notes</div>
