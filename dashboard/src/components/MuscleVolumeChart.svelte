<script lang="ts">
  import { onMount } from 'svelte';
  import { muscleChart, muscleHit, type MuscleBands } from '../muscleChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { onResizePaint } from '../lib/paint';

  interface Props {
    id?: string;
    labels: string[];
    counts: number[];
    bands: MuscleBands;
    color: string;
    height?: string;
  }

  let { id = undefined, labels, counts, bands, color, height = undefined }: Props = $props();

  let cv: HTMLCanvasElement;

  function visible(): boolean {
    return cv.clientWidth > 0 && cv.clientHeight > 0;
  }

  function paint(hover = -1) {
    if (cv && visible()) muscleChart(cv, labels, counts, bands, color, hover);
  }

  function show(cx: number, cy: number) {
    if (!visible()) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const bi = muscleHit(cv, counts.length, cx - r.left);
    if (bi < 0) {
      hideTip();
      paint();
      return;
    }
    paint(bi);
    showTip(labels[bi], [[color, counts[bi] + ' sets (MEV ' + bands.mev + ')']], cx, cy);
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
    labels;
    counts;
    bands;
    color;
    paint();
  });
</script>

<canvas bind:this={cv} {id} width="860" height="250" style:height></canvas>
