<script lang="ts">
  import { onMount } from 'svelte';
  import { plot, type MuscleModel } from '../muscleChart';
  import { fmtD } from '../lib/format';
  import { bindHover, hideTip, showTip } from '../tip';
  import { markHit, type ChartMark } from '../charts';
  import { nearestPoint, emptyHit, type HitMap } from '../lib/chartLayout';
  import { canvasShell, isVisible } from '../lib/canvas';

  interface Props {
    id?: string;
    labels: string[];
    counts: number[];
    bands: MuscleModel['bands'];
    color: string;
    height?: string;
    marks?: ChartMark[];
    selDate?: string | null;
    onSelectMark?: (date: string) => void;
  }

  let {
    id = undefined,
    labels,
    counts,
    bands,
    color,
    height = undefined,
    marks = [],
    selDate = null,
    onSelectMark = undefined,
  }: Props = $props();

  let cv: HTMLCanvasElement;
  let hit: HitMap = emptyHit();
  let markByDate: Map<string, ChartMark> = new Map();

  const model: MuscleModel = $derived({ labels, counts, bands, color, marks, selDate });

  function paint(hover = -1) {
    if (isVisible(cv)) {
      hit = plot(cv, model, hover);
      markByDate = new Map(marks.map(m => [m.date, m]));
    }
  }

  function show(cx: number, cy: number) {
    if (!isVisible(cv)) {
      hideTip();
      return;
    }
    const r = cv.getBoundingClientRect();
    const mk = markHit(hit.marks, markByDate, cx - r.left, 16);
    if (mk && onSelectMark) {
      paint();
      const rows = mk.titles.map(t => [null, t] as [null, string]);
      showTip(fmtD(mk.date), rows.length ? rows : [[null, 'recorded change']], cx, cy);
      cv.style.cursor = 'pointer';
      return;
    }
    const p = nearestPoint(hit, cx - r.left, 30);
    if (!p) {
      hideTip();
      paint();
      return;
    }
    paint(p.index);
    showTip(labels[p.index], [[color, counts[p.index] + ' sets (MEV ' + bands.mev + ')']], cx, cy);
  }

  function click(ev: MouseEvent) {
    if (!onSelectMark) return;
    const r = cv.getBoundingClientRect();
    const mk = markHit(hit.marks, markByDate, ev.clientX - r.left, 20);
    if (mk) onSelectMark(mk.date);
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

<canvas bind:this={cv} {id} width="860" height="250" style:height></canvas>
