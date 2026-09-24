<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, type BwRow } from '../bwChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { nearestPoint, emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    rows: BwRow[];
  }

  let { rows }: Props = $props();

  let cv: HTMLCanvasElement;
  let hit: HitMap = emptyHit();

  function paint(hover = -1) {
    if (isVisible(cv)) hit = plot(cv, rows, hover);
  }

  function show(cx: number, cy: number) {
    if (!rows.length || !isVisible(cv)) {
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
    const row = rows[p.index];
    showTip(
      row.date,
      [
        [
          null,
          row.kg.toFixed(1) + ' kg' + (row.avg7 !== null ? ' · avg ' + row.avg7.toFixed(1) : ''),
        ],
      ],
      cx,
      cy
    );
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
