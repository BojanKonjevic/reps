<script lang="ts">
  import { onMount } from 'svelte';
  import { bwline } from '../bwChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    rows: Array<{ date: string; kg: number }>;
  }

  let { rows }: Props = $props();

  let cv: HTMLCanvasElement;

  function sliceIdx(x: number, cw: number, n: number): number {
    if (n <= 1) return 0;
    const i = Math.round((x - 46) / ((cw - 46 - 8) / (n - 1)));
    return Math.min(n - 1, Math.max(0, i));
  }

  function paint(hover = -1) {
    if (isVisible(cv)) bwline(cv, rows, hover);
  }

  function show(cx: number, cy: number) {
    if (!rows.length || !isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const idx = sliceIdx(cx - r.left, r.width, rows.length);
    paint(idx);
    showTip(rows[idx].date, [[null, rows[idx].kg.toFixed(1) + ' kg']], cx, cy);
  }

  canvasShell(() => paint());

  onMount(() => {
    bindHover(cv, show);
    const leave = () => {
      hideTip();
      paint();
    };
    cv.addEventListener('mouseleave', leave);
    return () => {
      cv.removeEventListener('mouseleave', leave);
    };
  });

  $effect(() => {
    paint();
  });
</script>

<canvas bind:this={cv} id="chBw" width="860" height="250"></canvas>
