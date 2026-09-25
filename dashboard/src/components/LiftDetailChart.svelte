<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, type LiftModel, type LiftPoint } from '../liftChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { nearestPoint, emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';
  import { href } from '../routes';

  interface Props {
    pts: LiftPoint[];
    color: string;
    futureEv?: number | null;
    asOf: string;
    marks?: string[];
  }

  let { pts, color, futureEv = null, asOf, marks = [] }: Props = $props();

  let cv: HTMLCanvasElement;
  let hit: HitMap = emptyHit();

  const model: LiftModel = $derived({ pts, color, futureEv, asOf, marks });

  function paint(hover = -1) {
    if (isVisible(cv)) hit = plot(cv, model, hover);
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const p = nearestPoint(hit, cx - r.left, 40);
    if (!p) {
      hideTip();
      paint();
      cv.style.cursor = 'default';
      return;
    }
    paint(p.index);
    const pt = pts[p.index];
    showTip(
      pt.date,
      [[null, pt.w + ' x ' + pt.r + ' (e1RM ' + pt.ev.toFixed(1) + ')' + (pt.pr ? ' PR' : '')]],
      cx,
      cy
    );
    cv.style.cursor = 'pointer';
  }

  function click(ev: MouseEvent) {
    const r = cv.getBoundingClientRect();
    const p = nearestPoint(hit, ev.clientX - r.left, 34);
    if (p) location.hash = href.session(pts[p.index].date);
  }

  canvasShell(() => paint());

  onMount(() => {
    bindHover(cv, show);
    cv.addEventListener('click', click);
    const leave = () => {
      hideTip();
      paint();
      cv.style.cursor = 'default';
    };
    cv.addEventListener('mouseleave', leave);
    return () => {
      cv.removeEventListener('click', click);
      cv.removeEventListener('mouseleave', leave);
    };
  });

  $effect(() => {
    paint();
  });
</script>

<canvas bind:this={cv} id="chLift" width="860" height="260"></canvas>
