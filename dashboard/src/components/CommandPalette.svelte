<script lang="ts">
  import { closePalette, palette } from '../lib/palette.svelte';
  import {
    paletteMovements,
    paletteMuscles,
    palettePages,
    paletteSessions,
    filterPalRows,
    type PalSection,
  } from '../lib/select';
  import type { Snapshot } from '../generated/snapshot';

  interface Props {
    snap: Snapshot;
  }

  let { snap }: Props = $props();

  let q = $state('');
  let active = $state(0);
  let input: HTMLInputElement | undefined = $state();

  const sections = $derived.by((): PalSection[] => {
    if (!q.trim()) return [{ header: '', rows: filterPalRows(palettePages(), '') }];
    const out: PalSection[] = [];
    const add = (header: string, rows: ReturnType<typeof filterPalRows>) => {
      if (rows.length) out.push({ header, rows });
    };
    add('Pages', filterPalRows(palettePages(), q));
    add('Movements', filterPalRows(paletteMovements(snap.lifts), q));
    add('Muscles', filterPalRows(paletteMuscles(snap.muscles), q));
    add('Sessions', filterPalRows(paletteSessions(snap.sessions), q));
    return out;
  });

  const flat = $derived(sections.flatMap(s => s.rows));

  function close() {
    closePalette();
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
    if (active > flat.length - 1) active = Math.max(0, flat.length - 1);
  });

  function key(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (flat.length) active = (active + 1) % flat.length;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (flat.length) active = (active - 1 + flat.length) % flat.length;
    } else if (e.key === 'Enter') {
      const row = flat[active];
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
    <div class="pal-panel" role="dialog" aria-modal="true" aria-label="jump anywhere">
      <input
        bind:this={input}
        value={q}
        oninput={e => {
          q = (e.target as HTMLInputElement).value;
          active = 0;
        }}
        onkeydown={key}
        placeholder="jump to..."
        aria-label="jump anywhere"
      />
      {#if !flat.length}
        <div class="pal-empty">nothing matches</div>
      {/if}
      {#each sections as sec}
        {#if sec.header}
          <div class="pal-sec">{sec.header}</div>
        {/if}
        {#each sec.rows as row}
          {@const gi = flat.indexOf(row)}
          <button
            type="button"
            class:pal-active={gi === active}
            onmouseenter={() => (active = gi)}
            onclick={() => go(row.href)}
          >
            <span class="pal-name">{row.label}</span>
            <span class="pal-sub">{row.sub}</span>
          </button>
        {/each}
      {/each}
      <div class="pal-foot">
        <span><kbd>↑↓</kbd> move</span><span><kbd>↵</kbd> open</span><span
          ><kbd>esc</kbd> close</span
        >
      </div>
    </div>
  </div>
{/if}
