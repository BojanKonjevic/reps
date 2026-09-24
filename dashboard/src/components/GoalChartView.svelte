<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, type GoalModel } from '../goalChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { fmtD, fmtV } from '../lib/format';
  import { nearestPoint, emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    id?: string;
    actuals: Array<{ date: string; ev: number }>;
    checkpoints: number[];
    color: string;
    tops?: Record<string, { w: number; r: number }>;
  }

  let { id = undefined, actuals, checkpoints, color, tops = {} }: Props = $props();

  let cv: HTMLCanvasElement;
  let hit: HitMap = emptyHit();

  const model: GoalModel = $derived({ actuals, checkpoints, color });

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
    const bi = p.index;
    paint(bi);
    if (bi < actuals.length) {
      const a = actuals[bi];
      const top = tops[a.date];
      const logged = top
        ? 'logged ' + top.w + ' x ' + top.r + ' (e1RM ' + fmtV(a.ev) + ')'
        : 'e1RM ' + fmtV(a.ev);
      showTip(
        fmtD(a.date),
        [
          [color, logged],
          [null, 'plan ' + fmtV(checkpoints[bi])],
        ],
        cx,
        cy
      );
    } else {
      showTip(
        'session ' + (bi + 1) + ' (plan)',
        [[color, 'target e1RM ' + fmtV(checkpoints[bi])]],
        cx,
        cy
      );
    }
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

<canvas bind:this={cv} {id} width="860" height="200"></canvas>
