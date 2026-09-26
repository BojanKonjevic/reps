<script lang="ts">
  // SSOT owner: as-of date control. Consumers: lift and muscle pages.
  // Today is the default (the charts themselves). Any date in range is
  // selectable; event dates carry dots as discovery aids, never restrictions.
  import { fmtD, isoParts, monthGrid, monthLabel, shiftMonth } from '../lib/format';

  interface Props {
    value: string | null;
    min: string | null;
    max: string;
    eventDates: string[];
    onPick: (date: string | null) => void;
    id?: string;
  }

  let { value, min, max, eventDates, onPick, id = undefined }: Props = $props();

  let open = $state(false);
  const dots = $derived(new Set(eventDates));

  let viewY = $state(0);
  let viewM = $state(0);

  function syncView(date: string) {
    const [y, m] = isoParts(date);
    viewY = y;
    viewM = m;
  }

  function toggle() {
    if (!open) syncView(value ?? max);
    open = !open;
  }

  function close() {
    open = false;
  }

  function pick(date: string | null) {
    onPick(date);
    close();
  }

  function step(delta: number) {
    const [y, m] = shiftMonth(viewY, viewM, delta);
    viewY = y;
    viewM = m;
  }

  function inRange(date: string): boolean {
    return (!min || date >= min) && date <= max;
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation();
      close();
    }
  }
</script>

<div class="asofctl" {id}>
  <button type="button" class="evbtn" onclick={toggle} aria-expanded={open} aria-haspopup="dialog">
    As of {value ? fmtD(value) : 'Today'} ▾
  </button>
  {#if open}
    <div class="asofback" onclick={close} aria-hidden="true"></div>
    <div
      class="asofpop"
      role="dialog"
      aria-label="Choose as-of date"
      tabindex={-1}
      onkeydown={onKey}
    >
      <div class="asofhead">
        <button type="button" aria-label="Previous year" onclick={() => step(-12)}>«</button>
        <button type="button" aria-label="Previous month" onclick={() => step(-1)}>‹</button>
        <b>{monthLabel(viewY, viewM)}</b>
        <button type="button" aria-label="Next month" onclick={() => step(1)}>›</button>
        <button type="button" aria-label="Next year" onclick={() => step(12)}>»</button>
      </div>
      <div class="asofgrid" role="rowgroup">
        {#each ['Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa', 'Su'] as wd}
          <div class="asofwd">{wd}</div>
        {/each}
        {#each monthGrid(viewY, viewM) as week}
          {#each week as date}
            {#if date === null}
              <div></div>
            {:else}
              <button
                type="button"
                class="asofday"
                class:sel={value === date}
                disabled={!inRange(date)}
                aria-pressed={value === date}
                aria-label={date}
                onclick={() => pick(date)}
              >
                {parseInt(date.slice(8, 10), 10)}
                {#if dots.has(date)}<span class="asofdot" aria-hidden="true"></span>{/if}
              </button>
            {/if}
          {/each}
        {/each}
      </div>
      <button type="button" class="evbtn" onclick={() => pick(null)}>Back to today</button>
    </div>
  {/if}
</div>
