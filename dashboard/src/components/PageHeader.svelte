<script lang="ts">
  // Shared visual primitive: compact application page header.
  interface Props {
    title: string;
    sub?: string;
    titleId?: string;
    subId?: string;
  }

  let { title, sub = '', titleId = undefined, subId = undefined }: Props = $props();
</script>

<div class="phead">
  <h1 id={titleId}>{title}</h1>
  {#if sub}<div class="psub" id={subId}>{sub}</div>{/if}
</div>
