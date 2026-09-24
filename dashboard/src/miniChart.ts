// SSOT owner: mini-trend geometry. Consumers: TrendMini via plot() -> HitMap.

import { max, min } from 'd3-array';
import { fit, putText, drawYAxis } from './charts';
import { linearScale } from './lib/scales';
import { fmtV, fmtD, niceTicks } from './lib/format';
import { theme } from './lib/theme';
import { layoutOf as baseLayout, emptyHit, type ChartLayout, type HitMap } from './lib/chartLayout';

export interface MiniModel {
  days: string[];
  vals: Array<number | null>;
  color: string;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'mini');
}

export function plot(cv: HTMLCanvasElement, model: MiniModel, hover = -1): HitMap {
  const { days, vals, color } = model;
  const { g, W, H } = fit(cv);
  const L = layoutOf(W, H);
  const P = L.padL;
  const hit = emptyHit();
  g.clearRect(0, 0, W, H);
  g.font = theme.font(15, 600);
  const pts: number[] = [];
  for (let i = 0; i < vals.length; i += 1) if (vals[i] !== null) pts.push(i);
  if (!pts.length) {
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, 'no data', P, H / 2, 'left');
    return hit;
  }
  const raw = pts.map(pi => vals[pi]!);
  let mn = min(raw) ?? 0;
  let mx = max(raw) ?? 1;
  if (!(mx > mn)) mx = mn + 1;
  const pad = (mx - mn) * 0.3 || 1;
  mn = Math.max(0, mn - pad);
  mx += pad;
  const t = niceTicks(mn, mx, 2);
  mn = t.lo;
  mx = t.hi;
  const n = vals.length;
  const px = linearScale([0, Math.max(1, n - 1)], [P, W - L.padR]);
  const xOf = (i: number) => (n <= 1 ? W - L.padR : px(i));
  const py = linearScale([mn, mx], [H - 15, 6]);
  drawYAxis(g, W, H, P, t);
  g.strokeStyle = color;
  g.lineWidth = 2.5;
  g.lineJoin = 'round';
  g.beginPath();
  pts.forEach((pi, k) => {
    if (k === 0) g.moveTo(xOf(pi), py(vals[pi]!));
    else g.lineTo(xOf(pi), py(vals[pi]!));
  });
  g.stroke();
  g.fillStyle = color;
  pts.forEach(pi => {
    g.beginPath();
    g.arc(xOf(pi), py(vals[pi]!), 2.5, 0, 7);
    g.fill();
    hit.points.push({ x: xOf(pi), y: py(vals[pi]!), index: pi });
  });
  const li = pts[pts.length - 1];
  g.fillStyle = color;
  if (li > n / 2) putText(g, W, fmtV(vals[li]!), xOf(li) - 8, py(vals[li]!) - 10, 'right');
  else putText(g, W, fmtV(vals[li]!), xOf(li) + 8, py(vals[li]!) - 10, 'left');
  if (hover >= 0 && hover < n && vals[hover] !== null) {
    const x = xOf(hover);
    g.strokeStyle = theme.color('ink-dim');
    g.globalAlpha = 0.45;
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(x, 6);
    g.lineTo(x, H - 15);
    g.stroke();
    g.globalAlpha = 1;
    g.fillStyle = color;
    g.beginPath();
    g.arc(x, py(vals[hover]!), 5, 0, 7);
    g.fill();
  }
  g.fillStyle = theme.color('ink-dim');
  if (days.length > 1) {
    putText(g, W, fmtD(days[0]), P, H - 5, 'left');
    putText(g, W, fmtD(days[days.length - 1]), W - L.padR, H - 5, 'right');
  }
  return hit;
}
