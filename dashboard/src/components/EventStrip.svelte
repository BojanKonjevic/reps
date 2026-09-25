<script lang="ts">
  // SSOT owner: event-strip presentation. Consumers: every annotated view.
  // Shared temporal primitive: date-grouped event buttons beside a chart.
  import { fmtD } from '../lib/format';
  import type { DateGroup } from '../lib/temporal';

  interface Props {
    groups: DateGroup[];
    selectedId: number | null;
    onSelect: (id: number) => void;
    id?: string;
  }

  let { groups, selectedId, onSelect, id = undefined }: Props = $props();
</script>

{#if groups.length}
  <div class="evstrip" {id} role="list" aria-label="Training changes near this chart">
    {#each groups as g}
      {#each g.events as e, i}
        <button
          type="button"
          class="evbtn"
          class:sel={selectedId === e.id}
          aria-pressed={selectedId === e.id}
          onclick={() => onSelect(e.id)}
        >
          {#if i === 0}<span class="evdate">{fmtD(g.date)}</span>{/if}
          {e.title}
        </button>
      {/each}
    {/each}
  </div>
{/if}
