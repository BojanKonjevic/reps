<script lang="ts">
  import { palette } from '../lib/palette.svelte';
  import { palettePages, filterPages } from '../lib/select';

  let q = $state('');
  let active = $state(0);
  let input: HTMLInputElement | undefined = $state();

  const rows = $derived(filterPages(palettePages(), q));

  function close() {
    palette.open = false;
    q = '';
    active = 0;
  }

  function go(target: string) {
    location.hash = target;
    close();
  }

  $effect(() => {
    if (palette.open) {
      q = '';
      active = 0;
      requestAnimationFrame(() => input?.focus());
    }
  });

  $effect(() => {
    if (active > rows.length - 1) active = Math.max(0, rows.length - 1);
  });

  function key(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      close();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      active = Math.min(active + 1, Math.max(rows.length - 1, 0));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      active = Math.max(active - 1, 0);
    } else if (e.key === 'Enter') {
      const row = rows[active];
      if (row) {
        e.preventDefault();
        go(row.href);
      }
    }
  }
</script>

{#if palette.open}
  <div class="pal-backdrop" onclick={close} aria-hidden="true"></div>
  <div class="pal-wrap">
    <div class="pal-panel" role="dialog" aria-modal="true" aria-label="jump to page">
      <input
        bind:this={input}
        value={q}
        oninput={e => {
          q = (e.target as HTMLInputElement).value;
          active = 0;
        }}
        onkeydown={key}
        placeholder="jump to..."
        aria-label="jump to page"
      />
      {#if !rows.length}
        <div class="pal-empty">no page matches</div>
      {/if}
      {#each rows as row, i}
        <button
          type="button"
          class:pal-active={i === active}
          onmouseenter={() => (active = i)}
          onclick={() => go(row.href)}
        >
          <span class="pal-name">{row.label}</span>
          <span class="pal-sub">{row.sub}</span>
        </button>
      {/each}
      <div class="pal-foot">
        <span><kbd>↑↓</kbd> move</span><span><kbd>↵</kbd> open</span><span
          ><kbd>esc</kbd> close</span
        >
      </div>
    </div>
  </div>
{/if}
