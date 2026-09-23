<script lang="ts">
  import { onMount } from 'svelte';
  import { bwline } from '../bwChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { onResizePaint } from '../lib/paint';

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

  function visible(): boolean {
    return cv.clientWidth > 0 && cv.clientHeight > 0;
  }

  function paint(hover = -1) {
    if (cv && visible()) bwline(cv, rows, hover);
  }

  function show(cx: number, cy: number) {
    if (!rows.length || !visible()) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const idx = sliceIdx(cx - r.left, r.width, rows.length);
    paint(idx);
    showTip(rows[idx].date, [[null, rows[idx].kg.toFixed(1) + ' kg']], cx, cy);
  }

  onMount(() => {
    paint();
    bindHover(cv, show);
    const leave = () => {
      hideTip();
      paint();
    };
    cv.addEventListener('mouseleave', leave);
    const cleanupResize = onResizePaint(() => paint());
    return () => {
      cv.removeEventListener('mouseleave', leave);
      cleanupResize();
    };
  });

  $effect(() => {
    rows;
    paint();
  });
</script>

<canvas bind:this={cv} id="chBw" width="860" height="250"></canvas>
