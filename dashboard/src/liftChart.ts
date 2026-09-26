// SSOT owner: lift-detail chart geometry. Consumers: LiftDetailChart via plot() -> HitMap.

import {
  fit,
  putText,
  drawSingleLine,
  drawYAxis,
  drawXAxisLabels,
  drawHoverLine,
  drawEventTicks,
  drawPoint,
  drawHoverPoint,
  drawLine,
  type ChartMark,
} from './charts';
import { centeredDomain, linearScale, padDomain, timeScale, valueExtent } from './lib/scales';
import { fmtV, niceTicks, parseDate, type Ticks } from './lib/format';
import { theme } from './lib/theme';
import { layoutOf as baseLayout, emptyHit, type ChartLayout, type HitMap } from './lib/chartLayout';

export interface LiftPoint {
  date: string;
  w: number;
  r: number;
  ev: number;
  pr: boolean;
}

export interface LiftModel {
  pts: LiftPoint[];
  color: string;
  futureEv?: number | null;
  asOf: string;
  marks?: ChartMark[];
  selDate?: string | null;
}

export function layoutOf(w: number, h: number): ChartLayout {
  return baseLayout(w, h, 'full');
}

// Marks carrying a state change, clamped to the plotted span, oldest first.
// Same-date events collapse to one tick; the strip lists them all.
export function markDates(pts: LiftPoint[], marks: ChartMark[] | undefined): ChartMark[] {
  if (!marks || !pts.length) return [];
  const d0 = pts[0].date;
  const d1 = pts[pts.length - 1].date;
  const seen = new Set<string>();
  return marks.filter(m => {
    if (m.date < d0 || m.date > d1 || seen.has(m.date)) return false;
    seen.add(m.date);
    return true;
  });
}

export function plot(cv: HTMLCanvasElement, model: LiftModel, hover = -1): HitMap {
  const { pts, color, futureEv, asOf, marks, selDate } = model;
  const { g, W, H } = fit(cv);
  const L = layoutOf(W, H);
  const P = L.padL;
  const hit = emptyHit();
  g.clearRect(0, 0, W, H);
  g.font = theme.font(16, 600);
  if (!pts.length) {
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, 'no sets logged for this lift yet', P, H / 2, 'left');
    return hit;
  }
  const d0 = pts[0].date;
  const d1 = pts[pts.length - 1].date > asOf ? pts[pts.length - 1].date : asOf;
  const xScale = timeScale([d0, d1], [P, W - L.padR]);
  const xOf = (dt: string) => xScale(parseDate(dt));
  const ext = valueExtent(
    pts.map(p => p.ev).concat(futureEv !== undefined && futureEv !== null ? [futureEv] : [])
  ) || [0, 1];
  const showFuture = futureEv !== undefined && futureEv !== null && pts.length > 0;
  const single = pts.length === 1 && !showFuture;
  let mn: number;
  let mx: number;
  let t: Ticks | null = null;
  if (single) {
    [mn, mx] = centeredDomain(pts[0].ev);
  } else {
    const [plo, phi] = padDomain(ext, 0.25, 1);
    t = niceTicks(plo, phi, 4);
    mn = t.lo;
    mx = t.hi;
  }
  const py = linearScale([mn, mx], [H - P, 18]);
  if (t) drawYAxis(g, W, H, P, t);
  else drawSingleLine(g, W, P, L.padR, py(pts[0].ev), fmtV(pts[0].ev), H - P - 18);
  drawXAxisLabels(g, W, H, P, pts[0].date, single ? asOf : pts[pts.length - 1].date);
  const linePts = pts.map(p => ({ x: xOf(p.date), y: py(p.ev) }));
  g.fillStyle = theme.color('ink-dim');
  const fy0 = showFuture ? py(futureEv as number) : null;
  if (!single && (fy0 === null || Math.abs(py(pts[0].ev) - fy0) > 18))
    putText(g, W, fmtV(pts[0].ev) + ' start', linePts[0].x + 8, py(pts[0].ev) - 12, 'left');
  if (!single && !showFuture)
    putText(
      g,
      W,
      fmtV(pts[pts.length - 1].ev) + ' now',
      W - L.padR,
      py(pts[pts.length - 1].ev) - 12,
      'right'
    );
  drawLine(g, linePts, color);
  const ticked = markDates(pts, marks);
  drawEventTicks(
    g,
    ticked.map(m => xOf(m.date)),
    H - P,
    ticked.map(m => m.date === selDate)
  );
  for (const m of ticked) hit.marks.push({ x: xOf(m.date), date: m.date });
  pts.forEach((p, i) => {
    const x = xOf(p.date),
      y = py(p.ev);
    hit.points.push({ x, y, index: i });
    drawPoint(g, x, y, 4, color, false);
  });
  if (futureEv !== undefined && futureEv !== null && pts.length) {
    // Pinned to the right edge, never next to the last point: the target is
    // upcoming, not tomorrow. A date-meaningful x would need the next
    // scheduled day for this lift, which the snapshot does not emit.
    const fx = W - L.padR;
    const fy = py(futureEv);
    g.save();
    g.strokeStyle = color;
    g.globalAlpha = 0.85;
    g.setLineDash([4, 3]);
    g.lineWidth = 2;
    g.beginPath();
    g.moveTo(linePts[linePts.length - 1].x, linePts[linePts.length - 1].y);
    g.lineTo(fx, fy);
    g.stroke();
    g.restore();
    g.save();
    g.strokeStyle = color;
    g.lineWidth = 2;
    const s = 6;
    g.beginPath();
    g.moveTo(fx, fy - s);
    g.lineTo(fx + s, fy);
    g.lineTo(fx, fy + s);
    g.lineTo(fx - s, fy);
    g.closePath();
    g.stroke();
    g.restore();
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, fmtV(futureEv) + ' next', fx, fy - 10, 'right');
  }
  if (hover >= 0 && hover < pts.length) {
    const p = pts[hover];
    const x = xOf(p.date);
    drawHoverLine(g, H, P, x);
    drawHoverPoint(g, x, py(p.ev), 6, color, false);
  }
  return hit;
}
