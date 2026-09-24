<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, type MuscleModel } from '../muscleChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { nearestPoint, emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    id?: string;
    labels: string[];
    counts: number[];
    bands: MuscleModel['bands'];
    color: string;
    height?: string;
  }

  let { id = undefined, labels, counts, bands, color, height = undefined }: Props = $props();

  let cv: HTMLCanvasElement;
  let hit: HitMap = emptyHit();

  const model: MuscleModel = $derived({ labels, counts, bands, color });

  function paint(hover = -1) {
    if (isVisible(cv)) hit = plot(cv, model, hover);
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const p = nearestPoint(hit, cx - r.left, 30);
    if (!p) {
      hideTip();
      paint();
      return;
    }
    paint(p.index);
    showTip(labels[p.index], [[color, counts[p.index] + ' sets (MEV ' + bands.mev + ')']], cx, cy);
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

<canvas bind:this={cv} {id} width="860" height="250" style:height></canvas>
