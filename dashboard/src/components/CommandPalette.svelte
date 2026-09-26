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
  let panel: HTMLDivElement | undefined = $state();
  let opener: Element | null = null;
  let wasOpen = $state(false);

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
  const activeId = $derived(
    flat.length ? 'pal-' + flat[Math.min(active, flat.length - 1)].key : undefined
  );

  function restoreFocus() {
    if (opener instanceof HTMLElement && document.contains(opener)) opener.focus();
    opener = null;
  }

  function close() {
    closePalette();
  }

  function go(target: string) {
    location.hash = target;
    close();
  }

  $effect(() => {
    if (palette.open && !wasOpen) {
      wasOpen = true;
      opener = document.activeElement;
      q = '';
      active = 0;
      requestAnimationFrame(() => input?.focus());
    } else if (!palette.open && wasOpen) {
      wasOpen = false;
      q = '';
      active = 0;
      restoreFocus();
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
    } else if (e.key === 'Tab' && panel) {
      // Trap Tab inside the dialog: the input owns the keyboard state,
      // results are exposed through aria-activedescendant, never focus.
      const items = panel.querySelectorAll<HTMLElement>(
        'input:not([disabled]), button:not([disabled])'
      );
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
</script>

{#if palette.open}
  <div class="pal-backdrop" onclick={close} aria-hidden="true"></div>
  <div class="pal-wrap">
    <div
      class="pal-panel"
      role="dialog"
      aria-modal="true"
      aria-label="jump anywhere"
      bind:this={panel}
    >
      <input
        bind:this={input}
        role="combobox"
        aria-expanded="true"
        aria-controls="pal-list"
        aria-activedescendant={activeId}
        aria-autocomplete="list"
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
      <div role="listbox" id="pal-list" aria-label="results">
        {#each sections as sec}
          {#if sec.header}
            <div class="pal-sec" role="presentation">{sec.header}</div>
          {/if}
          {#each sec.rows as row}
            {@const gi = flat.indexOf(row)}
            <button
              type="button"
              role="option"
              id={'pal-' + row.key}
              aria-selected={gi === active}
              class:pal-active={gi === active}
              onmouseenter={() => (active = gi)}
              onclick={() => go(row.href)}
            >
              <span class="pal-name">{row.label}</span>
              <span class="pal-sub">{row.sub}</span>
            </button>
          {/each}
        {/each}
      </div>
      <div class="pal-foot">
        <span><kbd>↑↓</kbd> move</span><span><kbd>↵</kbd> open</span><span
          ><kbd>esc</kbd> close</span
        >
      </div>
    </div>
  </div>
{/if}
