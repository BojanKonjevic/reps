// SSOT owner: goal-trajectory geometry. Consumers: GoalChartView via plot() -> HitMap.

import { max, min } from 'd3-array';
import { fit, putText, drawHoverLine } from './charts';
import { linearScale } from './lib/scales';
import { fmtV, fmtD, niceTicks } from './lib/format';
import { theme } from './lib/theme';
import {
  layoutOf as baseLayout,
  emptyHit,
  labelIndices,
  type ChartLayout,
  type HitMap,
} from './lib/chartLayout';

export interface GoalPoint {
  date: string;
  ev: number;
}

export interface GoalModel {
  actuals: GoalPoint[];
  checkpoints: number[];
  color: string;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'goal');
}

export function plot(cv: HTMLCanvasElement, model: GoalModel, hover = -1): HitMap {
  const { actuals, checkpoints, color: col } = model;
  const { g, W, H } = fit(cv);
  const L = layoutOf(W, H);
  const P = L.padL;
  const hit = emptyHit();
  g.clearRect(0, 0, W, H);
  g.font = theme.font(15, 600);
  const n = Math.max(actuals.length, checkpoints.length);
  if (!n) {
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, 'no trajectory yet', P, H / 2, 'left');
    return hit;
  }
  const all = actuals.map(a => a.ev).concat(checkpoints);
  let mn = min(all) ?? 0;
  let mx = max(all) ?? 1;
  const pad = (mx - mn) * 0.3 || 1;
  mn = Math.max(0, mn - pad);
  mx += pad;
  const t = niceTicks(mn, mx, 2);
  mn = t.lo;
  mx = t.hi;
  const px = linearScale([0, Math.max(1, n - 1)], [P, W - 6]);
  const xOf = (i: number) => (n <= 1 ? W - 6 : px(i));
  const py = linearScale([mn, mx], [H - 15, 6]);
  const nt = Math.round((t.hi - t.lo) / t.step);
  for (let i = 0; i <= nt; i += 1) {
    const v = parseFloat((t.lo + i * t.step).toPrecision(12));
    const y = py(v);
    g.strokeStyle = theme.color('line');
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(P, y);
    g.lineTo(W - 6, y);
    g.stroke();
    if (i % 2 === 0 || i === nt) {
      g.fillStyle = theme.color('ink-dim');
      putText(g, W, String(v), 2, y + 4, 'left');
    }
  }
  g.strokeStyle = col;
  g.lineWidth = 2.5;
  g.lineJoin = 'round';
  g.beginPath();
  actuals.forEach((a, i) => {
    if (i === 0) g.moveTo(xOf(i), py(a.ev));
    else g.lineTo(xOf(i), py(a.ev));
  });
  g.stroke();
  g.fillStyle = col;
  actuals.forEach((a, i) => {
    g.beginPath();
    g.arc(xOf(i), py(a.ev), 3, 0, 7);
    g.fill();
    hit.points.push({ x: xOf(i), y: py(a.ev), index: i });
  });
  g.strokeStyle = col;
  g.globalAlpha = 0.75;
  g.setLineDash([5, 4]);
  g.lineWidth = 2;
  g.beginPath();
  checkpoints.forEach((cp, i) => {
    if (i === 0) g.moveTo(xOf(i), py(cp));
    else g.lineTo(xOf(i), py(cp));
  });
  g.stroke();
  g.setLineDash([]);
  g.globalAlpha = 1;
  checkpoints.forEach((cp, i) => {
    if (i < actuals.length) return;
    g.strokeStyle = col;
    g.lineWidth = 2;
    g.beginPath();
    g.arc(xOf(i), py(cp), 4, 0, 7);
    g.stroke();
  });
  if (hover >= 0 && hover < n) {
    const hv = hover < actuals.length ? actuals[hover].ev : checkpoints[hover];
    if (hv !== undefined) {
      const x = xOf(hover);
      drawHoverLine(g, H, P, x);
      g.fillStyle = col;
      g.beginPath();
      g.arc(x, py(hv), 5, 0, 7);
      g.fill();
    }
  }
  g.fillStyle = theme.color('ink-dim');
  if (actuals.length) {
    const show = new Set(labelIndices(actuals.length, 3));
    actuals.forEach((a, i) => {
      // The goal value owns the right edge; keep date labels clear of it.
      if (show.has(i) && xOf(i) < W - 90) putText(g, W, fmtD(a.date), xOf(i), H - 5, 'center');
    });
    putText(g, W, fmtV(checkpoints[checkpoints.length - 1]) + ' goal', W - 6, H - 5, 'right');
  }
  return hit;
}
