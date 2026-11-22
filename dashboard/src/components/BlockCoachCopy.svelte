<script lang="ts">
  let { note }: { note: string } = $props();

  const headings = $derived([
    ...note.matchAll(/^(Progress|What held|Context|Next block):[ \t]*/gim),
  ]);
  const intro = $derived(note.slice(0, headings[0]?.index).trim());
  const sections = $derived(
    headings.map((heading, i) => ({
      label: heading[1],
      text: note.slice(heading.index + heading[0].length, headings[i + 1]?.index).trim(),
    }))
  );
</script>

<div class="coach-copy">
  {#if intro}<p>{intro}</p>{/if}
  {#each sections as { label, text }}
    <div class="part">
      <h3
        class:progress={label.toLowerCase() === 'progress'}
        class:next={label.toLowerCase() === 'next block'}
      >
        {label}
      </h3>
      {#if text}<p>{text}</p>{/if}
    </div>
  {/each}
</div>

<style>
  .coach-copy {
    display: grid;
    gap: 10px;
    margin: 0 0 16px;
    color: var(--ink-dim);
    font-size: 0.86rem;
  }
  h3 {
    margin: 0 0 2px;
    color: var(--ink);
    font-size: inherit;
    font-weight: 600;
  }
  .progress {
    color: var(--good);
  }
  .next {
    color: var(--link);
  }
  p {
    margin: 0;
    line-height: 1.5;
    white-space: pre-line;
  }
</style>
