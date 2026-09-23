<script lang="ts">
  import { onMount } from 'svelte';
  import { goalChart, goalHit } from '../goalChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { fmtD, fmtV } from '../utils';
  import { liftColor } from '../charts';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    id?: string;
    actuals: Array<{ date: string; ev: number }>;
    checkpoints: number[];
    exercise: string;
    tops?: Record<string, { w: number; r: number }>;
  }

  let { id = undefined, actuals, checkpoints, exercise, tops = {} }: Props = $props();

  let cv: HTMLCanvasElement;
  const col = $derived(liftColor(exercise));

  function paint(hover = -1) {
    if (isVisible(cv)) goalChart(cv, actuals, checkpoints, col, hover);
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const bi = goalHit(cv, actuals, checkpoints, cx - r.left);
    if (bi < 0) {
      hideTip();
      paint();
      return;
    }
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
          [col, logged],
          [null, 'plan ' + fmtV(checkpoints[bi])],
        ],
        cx,
        cy
      );
    } else {
      showTip(
        'session ' + (bi + 1) + ' (plan)',
        [[col, 'target e1RM ' + fmtV(checkpoints[bi])]],
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
    actuals;
    checkpoints;
    exercise;
    paint();
  });
</script>

<canvas bind:this={cv} {id} width="860" height="200"></canvas>
