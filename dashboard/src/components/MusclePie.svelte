<script lang="ts">
  import { onMount } from 'svelte';
  import { pieChart, pieHit, piePalette, type PieSlice } from '../pieChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    slices: PieSlice[];
    sets: number[];
  }

  let { slices, sets }: Props = $props();

  let cv: HTMLCanvasElement;

  function paint(hover = -1) {
    if (isVisible(cv)) pieChart(cv, slices, hover);
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
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

  canvasShell(() => paint());

  onMount(() => {
    bindHover(cv, show);
    cv.addEventListener('click', click);
    const leave = () => {
      hideTip();
      paint();
    };
    cv.addEventListener('mouseleave', leave);
    return () => {
      cv.removeEventListener('click', click);
      cv.removeEventListener('mouseleave', leave);
    };
  });

  $effect(() => {
    slices;
    sets;
    paint();
  });
</script>

<canvas bind:this={cv} id="chMusPie" width="240" height="240"></canvas>
