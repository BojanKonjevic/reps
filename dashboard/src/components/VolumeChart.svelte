<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, stackedHitFromMap, type StackedModel, type StackedHover } from '../stackedChart';
  import { bindHover, hideTip, showTip } from '../tip';
  import { emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    labels: string[];
    weeks: Array<Record<string, number>>;
    groups: string[];
    colors: Record<string, string>;
    mevOf: (muscle: string) => number;
    onSelect?: (muscle: string) => void;
  }

  let { labels, weeks, groups, colors, mevOf, onSelect }: Props = $props();

  let cv: HTMLCanvasElement;
  let hover: StackedHover | null = $state(null);
  let hit: HitMap = emptyHit();

  const model: StackedModel = $derived({ labels, weeks, groups, colors });

  function paint() {
    if (isVisible(cv)) hit = plot(cv, model, hover);
  }

  function point(ev: MouseEvent): StackedHover | null {
    const r = cv.getBoundingClientRect();
    return stackedHitFromMap(hit, ev.clientX - r.left, ev.clientY - r.top);
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const h = stackedHitFromMap(hit, cx - r.left, cy - r.top);
    if (!h) {
      hideTip();
      hover = null;
      paint();
      return;
    }
    hover = h;
    paint();
    const mev = mevOf(h.g);
    showTip(
      labels[h.wi],
      [
        [
          colors[h.g],
          h.g + ' ' + weeks[h.wi][h.g] + ' sets' + (mev > 0 ? ' (MEV ' + mev + ')' : ''),
        ],
      ],
      cx,
      cy
    );
  }

  function click(ev: MouseEvent) {
    const h = point(ev);
    if (h && onSelect) onSelect(h.g);
  }

  canvasShell(() => paint());

  onMount(() => {
    bindHover(cv, show);
    cv.addEventListener('click', click);
    const leave = () => {
      hideTip();
      hover = null;
      paint();
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

<canvas bind:this={cv} id="chMus" width="860" height="250"></canvas>
