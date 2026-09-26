<script lang="ts">
  // Shared visual primitive: quiet section header with optional action link.
  interface Props {
    title: string;
    sub?: string;
    actionLabel?: string;
    actionHref?: string;
  }

  let { title, sub = '', actionLabel = '', actionHref = '' }: Props = $props();
</script>

<div class="sec">
  <div class="sec-title">
    <h2>{title}</h2>
    {#if actionLabel && actionHref}<a class="sec-action" href={actionHref}>{actionLabel}</a>{/if}
  </div>
  {#if sub}<div class="sec-sub">{sub}</div>{/if}
</div>
