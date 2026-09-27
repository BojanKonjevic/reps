<script lang="ts">
  // SSOT owner: provenance presentation. Consumers: every chart card.
  // Shared temporal primitive: backend-owned observation definition.
  import type { ObservationDef } from '../generated/snapshot';

  interface Props {
    def: ObservationDef | null;
    id?: string;
  }

  let { def, id = undefined }: Props = $props();
</script>

{#if def}
  <details class="prov" {id}>
    <summary>How this is calculated</summary>
    <div class="provbody">
      <div>{def.definition}</div>
      {#if def.based_on?.length}
        <div class="cap">Based on</div>
        {#each def.based_on as b}
          <div>{b}</div>
        {/each}
      {/if}
      <details class="provtech">
        <summary>Technical details</summary>
        <div><b>{def.metric}</b> ({def.subject_kind})</div>
        <div class="cap">Sources</div>
        {#each def.sources as s}
          <div>{s}</div>
        {/each}
      </details>
    </div>
  </details>
{/if}
