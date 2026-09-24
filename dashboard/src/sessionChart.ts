// SSOT owner: session-length chart geometry. Consumers: SessionLengthChart via plot() -> HitMap.
// Durations and day labels arrive in the model (Python owns the first-to-last-set
// span); day colors arrive per point, resolved by the component in dayColor.

import { max, min } from 'd3-array';
import { fit, putText, drawYAxis } from './charts';
import { linearScale } from './lib/scales';
import { fmtD, fmtMin, niceTicks } from './lib/format';
import { theme } from './lib/theme';
import { layoutOf as baseLayout, emptyHit, type ChartLayout, type HitMap } from './lib/chartLayout';

export interface SessPoint {
  date: string;
  minutes: number;
  day: string;
  color: string;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'full');
}

export function plot(cv: HTMLCanvasElement, points: SessPoint[], hover = -1): HitMap {
  const { g, W, H } = fit(cv);
  const L = layoutOf(W, H);
  const P = L.padL;
  const hit = emptyHit();
  g.clearRect(0, 0, W, H);
  g.font = theme.font(16, 600);
  if (!points.length) {
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, 'no sessions yet, lengths appear here', P, H / 2, 'left');
    return hit;
  }
  const vals = points.map(p => p.minutes);
  let mn = min(vals) ?? 0,
    mx = max(vals) ?? 1;
  const pad = (mx - mn) * 0.5 || 1;
  mn -= pad;
  mx += pad;
  const t = niceTicks(mn, mx, 3);
  mn = t.lo;
  mx = t.hi;
  const px = linearScale([0, Math.max(1, points.length - 1)], [P, W - L.padR]);
  const xOf = (i: number) => (points.length === 1 ? W - L.padR : px(i));
  const py = linearScale([mn, mx], [H - P, 16]);
  drawYAxis(g, W, H, P, t);
  g.strokeStyle = theme.color('ink-faint');
  g.lineWidth = 2.5;
  g.lineJoin = 'round';
  g.beginPath();
  points.forEach((p, i) => {
    if (i === 0) g.moveTo(xOf(i), py(p.minutes));
    else g.lineTo(xOf(i), py(p.minutes));
  });
  g.stroke();
  points.forEach((p, i) => {
    g.fillStyle = p.color;
    g.beginPath();
    g.arc(xOf(i), py(p.minutes), hover === i ? 6 : 4, 0, 7);
    g.fill();
    hit.points.push({ x: xOf(i), y: py(p.minutes), index: i });
  });
  g.fillStyle = theme.color('ink-dim');
  putText(g, W, fmtMin(points[0].minutes), P + 4, py(points[0].minutes) - 12, 'left');
  const li = points.length - 1;
  if (li > 0)
    putText(g, W, fmtMin(points[li].minutes), W - L.padR - 4, py(points[li].minutes) - 12, 'right');
  putText(g, W, fmtD(points[0].date), P, H - 8, 'left');
  putText(g, W, fmtD(points[li].date), W - L.padR, H - 8, 'right');
  if (hover >= 0 && hover < points.length) {
    const x = xOf(hover);
    g.strokeStyle = theme.color('ink-dim');
    g.globalAlpha = 0.45;
    g.lineWidth = 1;
    g.beginPath();
    g.moveTo(x, 14);
    g.lineTo(x, H - P);
    g.stroke();
    g.globalAlpha = 1;
  }
  return hit;
}
