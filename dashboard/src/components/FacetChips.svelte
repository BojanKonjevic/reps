<script lang="ts">
  // SSOT owner: facet-chip loops. Consumers: dashboard and list pages.
  interface Props {
    facets: Array<[string, string]>;
    active: Set<string>;
    onToggle: (facet: string) => void;
    onReset?: () => void;
  }

  let { facets, active, onToggle, onReset }: Props = $props();
</script>

<span class="legend">
  {#if onReset}
    <button type="button" class="chip mini" onclick={onReset}>Reset</button>
  {/if}
  {#each facets as [label, facet]}
    <button
      type="button"
      class="chip mini"
      class:off={!active.has(facet)}
      data-facet={facet}
      aria-pressed={active.has(facet)}
      onclick={() => onToggle(facet)}>{label}</button
    >
  {/each}
</span>
