<script lang="ts">
  import { onMount } from 'svelte';
  import { stacked, stackedHit, type StackedHit } from '../stackedChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { MC } from '../charts';
  import { onResizePaint } from '../lib/paint';

  interface Props {
    labels: string[];
    weeks: Array<Record<string, number>>;
    mevOf: (muscle: string) => number;
    onSelect?: (muscle: string) => void;
  }

  let { labels, weeks, mevOf, onSelect }: Props = $props();

  let cv: HTMLCanvasElement;
  let hover: StackedHit | null = $state(null);

  function visible(): boolean {
    return cv.clientWidth > 0 && cv.clientHeight > 0;
  }

  function paint() {
    if (cv && visible()) stacked(cv, labels, weeks, hover);
  }

  function show(cx: number, cy: number) {
    if (!visible()) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const hit = stackedHit(cv, labels, weeks, cx - r.left, cy - r.top);
    if (!hit) {
      hideTip();
      hover = null;
      paint();
      return;
    }
    hover = hit;
    paint();
    const mev = mevOf(labels[hit.wi]);
    showTip(
      labels[hit.wi],
      [
        [
          MC[hit.g],
          hit.g + ' ' + weeks[hit.wi][hit.g] + ' sets' + (mev > 0 ? ' (MEV ' + mev + ')' : ''),
        ],
      ],
      cx,
      cy
    );
  }

  function click(ev: MouseEvent) {
    const r = cv.getBoundingClientRect();
    const hit = stackedHit(cv, labels, weeks, ev.clientX - r.left, ev.clientY - r.top);
    if (hit && onSelect) onSelect(hit.g);
  }

  onMount(() => {
    paint();
    bindHover(cv, show);
    cv.addEventListener('click', click);
    const leave = () => {
      hideTip();
      hover = null;
      paint();
    };
    cv.addEventListener('mouseleave', leave);
    const cleanupResize = onResizePaint(() => paint());
    return () => {
      cv.removeEventListener('click', click);
      cv.removeEventListener('mouseleave', leave);
      cleanupResize();
    };
  });

  $effect(() => {
    labels;
    weeks;
    paint();
  });
</script>

<canvas bind:this={cv} id="chMus" width="860" height="250"></canvas>
