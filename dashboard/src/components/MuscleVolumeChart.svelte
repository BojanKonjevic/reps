<script lang="ts">
  import { onMount } from 'svelte';
  import { muscleChart, muscleHit, type MuscleBands } from '../muscleChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { canvasShell, isVisible } from '../lib/canvas';

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

  function paint(hover = -1) {
    if (isVisible(cv)) muscleChart(cv, labels, counts, bands, color, hover);
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
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
    labels;
    counts;
    bands;
    color;
    paint();
  });
</script>

<canvas bind:this={cv} {id} width="860" height="250" style:height></canvas>
