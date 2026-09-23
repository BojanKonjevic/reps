<script lang="ts">
  import { onMount } from 'svelte';
  import { mini } from '../miniChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { fmtV } from '../utils';
  import { onResizePaint } from '../lib/paint';

  interface Props {
    days: string[];
    vals: Array<number | null>;
    color: string;
    meta?: Array<{ w: number; r: number } | null>;
    prDates?: Record<string, boolean>;
  }

  let { days, vals, color, meta = [], prDates = {} }: Props = $props();

  let cv: HTMLCanvasElement;

  function visible(): boolean {
    return cv.clientWidth > 0 && cv.clientHeight > 0;
  }

  function paint(hover = -1) {
    if (cv && visible()) mini(cv, days, vals, color, hover);
  }

  function show(cx: number, cy: number) {
    if (!visible()) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const n = vals.length;
    const x = cx - r.left;
    let bi = -1;
    let bd = 1e9;
    for (let k = 0; k < n; k += 1) {
      if (vals[k] === null) continue;
      const px = 30 + (r.width - 30 - 6) * (n <= 1 ? 1 : k / (n - 1));
      const d = Math.abs(px - x);
      if (d < bd) {
        bd = d;
        bi = k;
      }
    }
    if (bi < 0 || bd > 30) {
      hideTip();
      paint();
      return;
    }
    paint(bi);
    const m = meta[bi];
    const detail = m ? ' (' + m.w + ' x ' + m.r + ')' : '';
    showTip(
      days[bi],
      [[color, fmtV(vals[bi]!) + detail + (prDates[days[bi]] ? ' PR' : '')]],
      cx,
      cy
    );
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
    days;
    vals;
    color;
    paint();
  });
</script>

<canvas bind:this={cv}></canvas>
