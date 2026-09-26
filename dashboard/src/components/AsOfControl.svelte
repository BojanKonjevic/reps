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
  let trigger: HTMLButtonElement | undefined = $state();
  let pop: HTMLDivElement | undefined = $state();
  let opener: Element | null = null;
  const dots = $derived(new Set(eventDates));

  let viewY = $state(0);
  let viewM = $state(0);

  function syncView(date: string) {
    const [y, m] = isoParts(date);
    viewY = y;
    viewM = m;
  }

  function toggle() {
    setOpen(!open);
  }

  function close() {
    setOpen(false);
  }

  function pick(date: string | null) {
    onPick(date);
    setOpen(false);
  }

  function setOpen(v: boolean) {
    if (v === open) return;
    if (v) {
      opener = document.activeElement;
      syncView(value ?? max);
      open = true;
      // First meaningful control: month navigation at the top of the dialog.
      requestAnimationFrame(() => {
        pop?.querySelector<HTMLElement>('button')?.focus();
      });
    } else {
      open = false;
      if (opener instanceof HTMLElement && document.contains(opener)) opener.focus();
      opener = null;
    }
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
      setOpen(false);
    } else if (e.key === 'Tab' && pop) {
      const items = pop.querySelectorAll<HTMLElement>('button:not([disabled])');
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
</script>

<div class="asofctl" {id}>
  <button
    type="button"
    class="evbtn"
    class:set={value !== null}
    bind:this={trigger}
    onclick={toggle}
    aria-expanded={open}
    aria-haspopup="dialog"
  >
    As of {value ? fmtD(value) : 'Today'} ▾
  </button>
  {#if open}
    <div class="asofback" onclick={close} aria-hidden="true"></div>
    <div
      class="asofpop"
      role="dialog"
      aria-modal="true"
      aria-label="Choose as-of date"
      tabindex={-1}
      bind:this={pop}
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
