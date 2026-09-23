<script lang="ts">
  import { onMount } from 'svelte';
  import { getLiftPts, liftChart, type LiftPoint } from '../liftChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    pts: LiftPoint[];
    exercise: string;
    futureEv?: number | null;
  }

  let { pts, exercise, futureEv = null }: Props = $props();

  let cv: HTMLCanvasElement;

  function paint(hover = -1) {
    if (isVisible(cv)) liftChart(cv, pts, exercise, hover, futureEv);
  }

  function near(ev: MouseEvent): { x: number; y: number; date: string } | null {
    const r = cv.getBoundingClientRect();
    const x = ev.clientX - r.left;
    const y = ev.clientY - r.top;
    let best: { x: number; y: number; date: string } | null = null;
    let bd = 1e9;
    for (const p of getLiftPts()) {
      const d = Math.abs(p.x - x) + Math.abs(p.y - y);
      if (d < bd) {
        bd = d;
        best = p;
      }
    }
    return bd < 34 ? best : null;
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const x = cx - r.left;
    let bi = -1;
    let bd = 1e9;
    getLiftPts().forEach((p, i) => {
      const d = Math.abs(p.x - x);
      if (d < bd) {
        bd = d;
        bi = i;
      }
    });
    if (bi < 0 || bd > 40) {
      hideTip();
      paint();
      cv.style.cursor = 'default';
      return;
    }
    paint(bi);
    const p = pts[bi];
    showTip(
      p.date,
      [[null, p.w + ' x ' + p.r + ' (e1RM ' + p.ev.toFixed(1) + ')' + (p.pr ? ' PR' : '')]],
      cx,
      cy
    );
    cv.style.cursor = 'pointer';
  }

  function click(ev: MouseEvent) {
    const p = near(ev);
    if (p) location.hash = '#/s/' + p.date;
  }

  canvasShell(() => paint());

  onMount(() => {
    bindHover(cv, show);
    cv.addEventListener('click', click);
    const mouse = (ev: MouseEvent) => {
      cv.style.cursor = near(ev) ? 'pointer' : 'default';
    };
    cv.addEventListener('mousemove', mouse);
    const leave = () => {
      hideTip();
      paint();
      cv.style.cursor = 'default';
    };
    cv.addEventListener('mouseleave', leave);
    return () => {
      cv.removeEventListener('click', click);
      cv.removeEventListener('mousemove', mouse);
      cv.removeEventListener('mouseleave', leave);
    };
  });

  $effect(() => {
    pts;
    exercise;
    futureEv;
    paint();
  });
</script>

<canvas bind:this={cv} id="chLift" width="860" height="260"></canvas>
