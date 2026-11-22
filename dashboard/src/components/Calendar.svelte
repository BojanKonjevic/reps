<script lang="ts">
  import { blockDisplay } from '../lib/blockDisplay.svelte';
  import { hideTip, showTip } from '../tip';
  import type { CalendarDay } from '../generated/snapshot';
  import { viewToday } from '../lib/clock';
  import { theme } from '../lib/theme';
  import { fmtHoverDate } from '../lib/format';
  import { href } from '../routes';
  import Icon from './Icon.svelte';

  interface Props {
    days: CalendarDay[];
  }

  let { days }: Props = $props();

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

  const byDate = $derived.by(() => {
    const m: Record<string, CalendarDay> = {};
    for (const d of days) m[d.date] = d;
    return m;
  });

  const lastDay = $derived(days.length ? days[days.length - 1].date : viewToday());
  let viewY = $state(0);
  let viewM = $state(0);
  let shownScope = $state<number | null | undefined>(undefined);
  $effect(() => {
    const scope = blockDisplay.selected?.id ?? null;
    if (shownScope !== scope) {
      viewY = parseInt(lastDay.slice(0, 4), 10);
      viewM = parseInt(lastDay.slice(5, 7), 10) - 1;
      shownScope = scope;
    }
  });

  const todayS = viewToday();

  interface Cell {
    key: string;
    day: number;
    cls: string;
    link: boolean;
    pr: boolean;
  }

  const cells = $derived.by((): Array<Cell | null> => {
    const first = new Date(viewY, viewM, 1);
    let lead = first.getDay() - 1;
    if (lead < 0) lead = 6;
    const out: Array<Cell | null> = [];
    for (let i = 0; i < lead; i += 1) out.push(null);
    const monthDays = new Date(viewY, viewM + 1, 0).getDate();
    for (let d = 1; d <= monthDays; d += 1) {
      const key =
        viewY + '-' + String(viewM + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0');
      const info = byDate[key];
      const trained = info?.kind === 'trained';
      const rested = info?.kind === 'rest';
      out.push({
        key,
        day: d,
        cls:
          'cd' +
          (trained ? ' t' : '') +
          (rested ? ' r' : '') +
          (key === todayS ? ' today' : '') +
          (key > todayS ? ' fut' : '') +
          (info?.break_after_gap ? ' brk' : '') +
          (blockDisplay.boundaries.includes(key) ? ' block-edge' : ''),
        link: trained || rested,
        pr: info?.has_pr || false,
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

  function hoverDay(key: string, ev: MouseEvent) {
    hideTip();
    const info = byDate[key];
    const lines = info?.hover.lines.length ? info.hover.lines : ['tap to open'];
    const title =
      fmtHoverDate(key) +
      (info?.slot_label ? ' ' + info.slot_label : '') +
      (info?.has_pr ? '  PR' : '');
    showTip(
      title,
      lines.map(
        l =>
          [info?.has_pr && l.includes('(PR)') ? theme.color('warn') : null, l] as [
            string | null,
            string,
          ]
      ),
      ev.clientX,
      ev.clientY
    );
  }
</script>

<div class="calhead">
  <button id="calPrev" type="button" aria-label="Previous month" onclick={prev}>
    <Icon name="chevronLeft" size={18} />
  </button>
  <b id="calTitle">{MONTHS[viewM]} {viewY}</b>
  <button id="calNext" type="button" aria-label="Next month" onclick={next}>
    <Icon name="chevronRight" size={18} />
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
        href={href.session(c.key)}
        class={c.cls}
        onmousemove={ev => hoverDay(c.key, ev)}
        onmouseleave={hideTip}
        onclick={hideTip}
        >{c.day}{#if c.pr}<span class="prt" title="personal record"
            ><Icon name="trophy" size={14} /></span
          >{/if}</a
      >
    {:else}
      <div class={c.cls}>{c.day}</div>
    {/if}
  {/each}
</div>
<div class="cap">Tap a highlighted day for the session. Trophy marks a PR day.</div>
<div class="cap">Recent notes</div>

<style>
  .cd.block-edge {
    border-inline-start: 1px dashed var(--ink-faint);
  }
</style>
