<script lang="ts">
  import { onMount } from 'svelte';
  import { pieChart, pieHit, piePalette, type PieSlice } from '../pieChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { onResizePaint } from '../lib/paint';

  interface Props {
    slices: PieSlice[];
    sets: number[];
  }

  let { slices, sets }: Props = $props();

  let cv: HTMLCanvasElement;

  function visible(): boolean {
    return cv.clientWidth > 0 && cv.clientHeight > 0;
  }

  function paint(hover = -1) {
    if (cv && visible()) pieChart(cv, slices, hover);
  }

  function show(cx: number, cy: number) {
    if (!visible()) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const bi = pieHit(cv, slices, cx - r.left, cy - r.top);
    if (bi < 0) {
      hideTip();
      paint();
      return;
    }
    paint(bi);
    showTip(
      slices[bi].label,
      [
        [
          piePalette(slices[bi].label),
          sets[bi] + ' sets · ' + Math.round(slices[bi].frac * 100) + '%',
        ],
      ],
      cx,
      cy
    );
  }

  function click(ev: MouseEvent) {
    const r = cv.getBoundingClientRect();
    const bi = pieHit(cv, slices, ev.clientX - r.left, ev.clientY - r.top);
    const link = bi >= 0 ? slices[bi].link : null;
    if (link) location.hash = link;
  }

  onMount(() => {
    paint();
    bindHover(cv, show);
    cv.addEventListener('click', click);
    const leave = () => {
      hideTip();
      paint();
    };
    cv.addEventListener('mouseleave', leave);
    const cleanupResize = onResizePaint(() => paint());
    return () => {
      cv.removeEventListener('click', click);
      cv.removeEventListener('mouseleave', leave);
      cleanupResize();
    };
  });

  $effect(() => {
    slices;
    sets;
    paint();
  });
</script>

<canvas bind:this={cv} id="chMusPie" width="240" height="240"></canvas>
