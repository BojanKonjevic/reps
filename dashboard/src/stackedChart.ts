// SSOT owner: stacked volume geometry. Consumers: VolumeChart via plot() -> HitMap.
// Groups and colors arrive in the model from lib/vocab (snapshot constants).

import { max } from 'd3-array';
import { fit, putText } from './charts';
import { linearScale } from './lib/scales';
import { fmtTick, niceTicks } from './lib/format';
import { theme } from './lib/theme';
import { layoutOf as baseLayout, emptyHit, type ChartLayout, type HitMap } from './lib/chartLayout';

export interface StackedModel {
  labels: string[];
  weeks: Array<Record<string, number>>;
  groups: string[];
  colors: Record<string, string>;
}

export interface StackedHover {
  wi: number;
  g: string;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'full');
}

interface Layout {
  W: number;
  H: number;
  P: number;
  padR: number;
  area: number;
  mx: number;
  bw: number;
}

function layout(W: number, H: number, model: StackedModel): Layout {
  const P = 46;
  const padR = 8;
  const totals = model.weeks.map(w => model.groups.reduce((a, k) => a + (w[k] || 0), 0));
  const mx = niceTicks(0, Math.max(1, max(totals) ?? 1), 3).hi;
  return {
    W,
    H,
    P,
    padR,
    area: H - P - 42,
    mx,
    bw: (W - P - padR) / Math.max(1, model.weeks.length),
  };
}

function yOfWeek(L: Layout, v: number): number {
  return linearScale([0, L.mx], [L.H - L.P, L.H - L.P - L.area])(v);
}

export function plot(
  cv: HTMLCanvasElement,
  model: StackedModel,
  hover?: StackedHover | null
): HitMap {
  const { labels, weeks, groups, colors } = model;
  const { g, W, H } = fit(cv);
  const P = 46;
  const hit = emptyHit();
  g.clearRect(0, 0, W, H);
  const L = layout(W, H, model);
  const bw = L.bw;
  const t = niceTicks(0, L.mx, 3);
  g.font = theme.font(16, 600);
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = yOfWeek(L, v);
    g.strokeStyle = theme.color('line');
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(P, y);
    g.lineTo(W - L.padR, y);
    g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = theme.color('ink-dim');
      putText(g, W, fmtTick(v, t.step), 4, y + 4, 'left');
    }
  }
  weeks.forEach((w, i) => {
    let acc = 0;
    groups.forEach(gr => {
      const v = w[gr] || 0;
      acc += v;
      const h = (L.area * v) / L.mx;
      const x = L.P + i * L.bw + 3;
      const y = yOfWeek(L, acc);
      g.fillStyle = colors[gr] || theme.color('ink-faint');
      g.fillRect(x, y, bw - 6, h);
      if (h > 2) hit.bars.push({ x, y, w: bw - 6, h, index: i, tag: gr });
      if (hover && hover.wi === i && hover.g === gr) {
        g.fillStyle = theme.color('overlay-tick-strong');
        g.fillRect(x, y, bw - 6, h);
      }
    });
    const total = groups.reduce((a, k) => a + (w[k] || 0), 0);
    const top = yOfWeek(L, total);
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, String(total), P + i * bw + bw / 2, top - 10, 'center');
    const step = Math.ceil(weeks.length / 4);
    if (i === 0 || i === weeks.length - 1 || i % step === 0)
      putText(g, W, labels[i], P + i * bw + bw / 2, H - 8, 'center');
  });
  return hit;
}

export function stackedHitFromMap(hit: HitMap, x: number, y: number): StackedHover | null {
  for (const b of hit.bars) {
    if (x >= b.x && x <= b.x + b.w && y >= b.y && y <= b.y + b.h && b.tag) {
      return { wi: b.index, g: b.tag };
    }
  }
  return null;
}
