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
      <div><b>{def.metric}</b></div>
      <div>{def.definition}</div>
      <div class="cap">Sources: {def.sources.join(', ')}</div>
    </div>
  </details>
{/if}
