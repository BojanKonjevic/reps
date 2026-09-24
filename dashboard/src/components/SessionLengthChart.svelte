<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, type SessPoint } from '../sessionChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { fmtD, fmtMin } from '../lib/format';
  import { nearestPoint, emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    points: SessPoint[];
  }

  let { points }: Props = $props();

  let cv: HTMLCanvasElement;
  let hit: HitMap = emptyHit();

  function paint(hover = -1) {
    if (isVisible(cv)) hit = plot(cv, points, hover);
  }

  function show(cx: number, cy: number) {
    if (!points.length || !isVisible(cv)) {
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
    const row = points[p.index];
    showTip(fmtD(row.date), [[row.color, row.day + ' · ' + fmtMin(row.minutes)]], cx, cy);
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

<canvas bind:this={cv} id="chSessLen" width="860" height="250"></canvas>
