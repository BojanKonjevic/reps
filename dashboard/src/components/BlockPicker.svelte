<script lang="ts">
  import type { BlockView } from '../generated/snapshot';

  interface Props {
    blocks: BlockView[];
    selected: BlockView | null;
    onSelect: (id: number | null) => void;
    showBoundaryKey: boolean;
  }

  let { blocks, selected, onSelect, showBoundaryKey }: Props = $props();
</script>

{#if blocks.length}
  <div class="block-picker">
    <label for="block-scope">Training history</label>
    <select
      id="block-scope"
      value={selected?.id ?? ''}
      onchange={ev => onSelect(ev.currentTarget.value ? Number(ev.currentTarget.value) : null)}
    >
      <option value="">All time</option>
      {#each blocks.slice().reverse() as block (block.id)}
        <option value={block.id}>
          Block {block.id} · {block.start_date}{block.end_date
            ? ' to ' + block.end_date
            : ' · current'}
        </option>
      {/each}
    </select>
    {#if !selected && showBoundaryKey}<span class="boundary-key">Dashed lines mark block dates</span
      >{/if}
  </div>
{/if}

<style>
  .block-picker {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.55rem;
    margin-block: 0 0.8rem;
    color: var(--ink-dim);
    font-size: 0.8rem;
  }
  .boundary-key {
    color: var(--ink-mute);
  }
  select {
    max-width: 100%;
    padding: 0.36rem 0.55rem;
    border: 1px solid var(--line-soft);
    border-radius: var(--radius-sm);
    color: var(--ink);
    background: transparent;
    font: inherit;
  }
</style>
