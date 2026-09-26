// SSOT owner: lift-detail chart geometry. Consumers: LiftDetailChart via plot() -> HitMap.

import {
  fit,
  putText,
  drawSingleLine,
  drawYAxis,
  drawEventTicks,
  drawPoint,
  drawHoverLine,
  drawHoverPoint,
  drawLine,
  type ChartMark,
} from './charts';
import { centeredDomain, linearScale, padDomain, valueExtent } from './lib/scales';
import { fmtD, fmtV, niceTicks, parseDate, type Ticks } from './lib/format';
import { theme } from './lib/theme';
import {
  layoutOf as baseLayout,
  emptyHit,
  labelIndices,
  type ChartLayout,
  type HitMap,
} from './lib/chartLayout';

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
  futureText?: string | null;
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

// Ordinal session axis: sessions sit at 0..n-1, the next target one slot
// past last. Dates only label the ends, so every lift's trend and
// trajectory read the same regardless of calendar gaps. Event dates map to
// fractional slots by time interpolation; order is always preserved.
export function sessionIndexOf(dates: string[], target: string): number {
  if (!dates.length) return 0;
  if (target <= dates[0]) return 0;
  const last = dates.length - 1;
  if (target >= dates[last]) return last;
  let i = 0;
  while (i < last && dates[i + 1] < target) i += 1;
  const a = parseDate(dates[i]).getTime();
  const b = parseDate(dates[i + 1]).getTime();
  if (!(b > a)) return i;
  const t = parseDate(target).getTime();
  return i + Math.min(1, Math.max(0, (t - a) / (b - a)));
}

export function plot(cv: HTMLCanvasElement, model: LiftModel, hover = -1): HitMap {
  const { pts, color, futureEv, marks, selDate } = model;
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
  const n = pts.length;
  const dates = pts.map(p => p.date);
  const ext = valueExtent(
    pts.map(p => p.ev).concat(futureEv !== undefined && futureEv !== null ? [futureEv] : [])
  ) || [0, 1];
  const showFuture = futureEv !== undefined && futureEv !== null && n > 0;
  const single = n === 1 && !showFuture;
  // One slot per session plus one for the target; a lone point centers.
  const xScale =
    single || n === 0
      ? linearScale([-0.5, 0.5], [P, W - L.padR])
      : linearScale([0, showFuture ? n : n - 1], [P, W - L.padR]);
  const xOf = (i: number) => xScale(i);
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
  // Session dates at readable intervals under their own slots, never
  // just the ends: equal spacing would otherwise imply a scale that is
  // not there.
  g.fillStyle = theme.color('ink-dim');
  for (const i of labelIndices(n, 6)) putText(g, W, fmtD(dates[i]), xOf(i), H - 8, 'center');
  const linePts = pts.map((p, i) => ({ x: xOf(i), y: py(p.ev) }));
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
  const tickXs = ticked.map(m => xOf(sessionIndexOf(dates, m.date)));
  drawEventTicks(
    g,
    tickXs,
    H - P,
    ticked.map(m => m.date === selDate)
  );
  for (const m of ticked) hit.marks.push({ x: xOf(sessionIndexOf(dates, m.date)), date: m.date });
  pts.forEach((p, i) => {
    const x = xOf(i),
      y = py(p.ev);
    hit.points.push({ x, y, index: i });
    drawPoint(g, x, y, 4, color, false);
  });
  if (futureEv !== undefined && futureEv !== null && pts.length) {
    // One slot past last, always the same geometry: the target is
    // upcoming, not tomorrow. A date-meaningful x would need the next
    // scheduled day for this lift, which the snapshot does not emit.
    const fx = xOf(n);
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
    hit.points.push({ x: fx, y: fy, index: n });
    g.fillStyle = theme.color('ink-dim');
    putText(g, W, fmtV(futureEv) + ' next', fx, fy - 10, 'right');
  }
  if (hover >= 0 && hover <= n && n > 0) {
    const hx = xOf(hover);
    const hy = hover < n ? py(pts[hover].ev) : py(futureEv as number);
    drawHoverLine(g, H, P, hx);
    drawHoverPoint(g, hx, hy, 6, color, false);
  }
  return hit;
}
