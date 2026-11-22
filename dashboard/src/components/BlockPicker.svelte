<script lang="ts">
  import type { BlockView } from '../generated/snapshot';
  import { href } from '../routes';

  interface Props {
    blocks: BlockView[];
    selected: BlockView | null;
    onSelect: (id: number | null) => void;
    showSummary: boolean;
  }

  let { blocks, selected, onSelect, showSummary }: Props = $props();
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
    {#if !selected && showSummary}<span class="boundary-key">Dashed lines mark block dates</span
      >{/if}
  </div>
  {#if showSummary && selected && (selected.changes.length || selected.coach_note)}
    <div class="surface-flat block-summary" aria-label="Block summary">
      {#if selected.changes.length}
        <div>
          <h2>Changes from previous block</h2>
          <ul>
            {#each selected.changes as change (change.change_id)}
              {#each change.details as detail}
                <li><a href={href.history(change.change_id)}>{change.subject} · {detail}</a></li>
              {/each}
            {/each}
          </ul>
        </div>
      {/if}
      {#if selected.coach_note}
        <div>
          <h2>Final coach note</h2>
          <p>{selected.coach_note}</p>
        </div>
      {/if}
    </div>
  {/if}
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
  .block-summary {
    display: grid;
    gap: 1rem;
    margin-bottom: 1rem;
    padding: 0.75rem 1rem;
    border-inline-start: 2px solid var(--line-soft);
  }
  h2 {
    font-size: 0.9rem;
    margin: 0 0 0.35rem;
  }
  p,
  ul {
    margin: 0;
    color: var(--ink-dim);
    font-size: 0.86rem;
  }
  p {
    white-space: pre-line;
  }
  ul {
    padding-inline-start: 1.2rem;
  }
</style>
