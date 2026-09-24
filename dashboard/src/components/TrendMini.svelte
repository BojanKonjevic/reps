<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, type MiniModel } from '../miniChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { fmtV } from '../lib/format';
  import { nearestPoint, emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';
  import type { Lift } from '../generated/snapshot';

  interface Props {
    lift: Lift;
    days: string[];
    vals: Array<number | null>;
    color: string;
  }

  let { lift, days, vals, color }: Props = $props();

  let cv: HTMLCanvasElement;
  let hit: HitMap = emptyHit();

  const model: MiniModel = $derived({ days, vals, color });

  const metaOf = $derived.by(() => {
    const m: Record<number, { w: number; r: number } | null> = {};
    const byDate = new Map(lift.sessions.map(s => [s.date, s]));
    days.forEach((d, i) => {
      const s = byDate.get(d);
      m[i] = s ? { w: s.weight, r: s.reps } : null;
    });
    return m;
  });

  const prOf = $derived.by(() => {
    const m: Record<string, boolean> = {};
    for (const s of lift.sessions) if (s.is_pr) m[s.date] = true;
    return m;
  });

  function paint(hover = -1) {
    if (isVisible(cv)) hit = plot(cv, model, hover);
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const x = cx - r.left;
    const p = nearestPoint(hit, x, 30);
    if (!p || vals[p.index] === null) {
      hideTip();
      paint();
      return;
    }
    const bi = p.index;
    paint(bi);
    const m = metaOf[bi];
    const detail = m ? ' (' + m.w + ' x ' + m.r + ')' : '';
    showTip(days[bi], [[color, fmtV(vals[bi]!) + detail + (prOf[days[bi]] ? ' PR' : '')]], cx, cy);
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

<canvas bind:this={cv}></canvas>
