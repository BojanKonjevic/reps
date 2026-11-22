<script lang="ts">
  import { tick } from 'svelte';
  import type { BlockView } from '../generated/snapshot';
  import { fmtD } from '../lib/format';
  import Icon from './Icon.svelte';

  interface Props {
    blocks: BlockView[];
    selected: BlockView | null;
    onSelect: (id: number | null) => void;
    alignEnd?: boolean;
  }

  let { blocks, selected, onSelect, alignEnd = false }: Props = $props();
  let open = $state(false);
  let picker = $state<HTMLDivElement>();
  let trigger = $state<HTMLButtonElement>();
  let menu = $state<HTMLDivElement>();

  function range(block: BlockView): string {
    const startYear = block.start_date.slice(0, 4);
    const start = fmtD(block.start_date);
    if (!block.end_date) return 'Since ' + start + ', ' + startYear;
    const endYear = block.end_date.slice(0, 4);
    return (
      start +
      (startYear === endYear ? '' : ', ' + startYear) +
      ' to ' +
      fmtD(block.end_date) +
      ', ' +
      endYear
    );
  }

  async function toggle() {
    open = !open;
    if (open) {
      await tick();
      menu?.querySelector<HTMLButtonElement>('[aria-checked="true"]')?.focus();
    }
  }

  function close(restoreFocus = false) {
    open = false;
    if (restoreFocus) trigger?.focus();
  }

  function pick(id: number | null) {
    onSelect(id);
    close(true);
  }

  function outside(event: PointerEvent) {
    if (open && event.target instanceof Node && !picker?.contains(event.target)) close();
  }

  function leave(event: FocusEvent) {
    if (open && event.relatedTarget instanceof Node && !picker?.contains(event.relatedTarget))
      close();
  }

  function onKey(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.stopPropagation();
      close(true);
      return;
    }
    if (!menu || !['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    const items = Array.from(menu.querySelectorAll<HTMLButtonElement>('button'));
    const index = items.indexOf(event.currentTarget as HTMLButtonElement);
    const target =
      event.key === 'Home'
        ? 0
        : event.key === 'End'
          ? items.length - 1
          : (index + (event.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
    items[target]?.focus();
  }
</script>

<svelte:window onpointerdown={outside} />

{#snippet option(label: string, id: number | null, details?: string)}
  {@const active = (selected?.id ?? null) === id}
  <button
    type="button"
    role="menuitemradio"
    aria-checked={active}
    tabindex="-1"
    onclick={() => pick(id)}
    onkeydown={onKey}
    class:active
  >
    <span>
      <span>{label}</span>
      {#if details}<small>{details}</small>{/if}
    </span>
    {#if active}<span class="chosen" aria-hidden="true"></span>{/if}
  </button>
{/snippet}

{#if blocks.length}
  <div class="block-picker" class:alignEnd bind:this={picker} onfocusout={leave}>
    <div class="control">
      <button
        type="button"
        class="trigger"
        bind:this={trigger}
        onclick={toggle}
        aria-label={'Training history: ' + (selected ? 'Block ' + selected.id : 'All time')}
        aria-expanded={open}
        aria-haspopup="menu"
        aria-controls={open ? 'block-scope' : undefined}
      >
        <span class="calendar-icon"><Icon name="calendar" size={16} /></span>
        {selected ? 'Block ' + selected.id : 'All time'}
        <span class="chevron"><Icon name="chevronRight" size={12} /></span>
      </button>
      {#if open}
        <div
          id="block-scope"
          class="options"
          role="menu"
          aria-label="Training history"
          bind:this={menu}
        >
          {@render option('All time', null)}
          {#each blocks.slice().reverse() as block (block.id)}
            {@render option(
              'Block ' + block.id + (block.end_date ? '' : ' · Current'),
              block.id,
              range(block)
            )}
          {/each}
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .block-picker {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.55rem;
    margin-block: 0 0.8rem;
    font-size: 0.9rem;
  }
  .alignEnd {
    margin-block: 0;
  }
  .alignEnd .options {
    inset-inline-start: auto;
    inset-inline-end: 0;
  }
  .control {
    position: relative;
  }
  .chevron,
  .calendar-icon {
    color: var(--ink-mute);
  }
  .chevron,
  .calendar-icon {
    display: inline-flex;
  }
  .chevron {
    transform: rotate(90deg);
  }
  .trigger {
    display: flex;
    align-items: center;
    min-height: 40px;
    gap: 9px;
    padding: 0 13px;
    border: 1px solid var(--line-soft);
    border-radius: var(--radius-sm);
    color: var(--ink);
    background: transparent;
    font: inherit;
    cursor: pointer;
  }
  .options {
    position: absolute;
    z-index: 10;
    inset-block-start: calc(100% + 5px);
    inset-inline-start: 0;
    width: min(248px, calc(100vw - 36px));
    max-height: min(50vh, 320px);
    overflow: auto;
    box-sizing: border-box;
    padding: 4px;
    border: 1px solid var(--line-soft);
    border-radius: var(--radius-sm);
    background: var(--bg-raised);
  }
  .options button {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    width: 100%;
    padding: 8px 9px;
    border: 0;
    border-radius: var(--radius-sm);
    color: var(--ink-dim);
    background: transparent;
    font: inherit;
    text-align: start;
    cursor: pointer;
  }
  .options button:hover,
  .options button:focus-visible {
    background: var(--bg-hover);
  }
  .options button.active {
    color: var(--ink);
    font-weight: 600;
  }
  small {
    display: block;
    margin-top: 2px;
    color: var(--ink-mute);
    font-size: 0.72rem;
    font-weight: 400;
  }
  .chosen {
    width: 6px;
    height: 6px;
    flex: 0 0 auto;
    border-radius: 50%;
    background: var(--accent);
  }
</style>
