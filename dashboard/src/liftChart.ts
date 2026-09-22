import {
  fit,
  putText,
  LC,
  TC,
  GC,
  drawYAxis,
  drawXAxisLabels,
  drawHoverLine,
  drawPoint,
  drawHoverPoint,
  drawLine,
} from './charts';
import { fmtV, fmtD } from './utils';
import { niceTicks } from './utils';

export interface LiftPoint {
  date: string;
  w: number;
  r: number;
  ev: number;
  pr: boolean;
}

let LIFTPTS: Array<{ x: number; y: number; date: string }> = [];

export function liftChart(
  cv: HTMLCanvasElement,
  pts: LiftPoint[],
  ex: string,
  hover?: number,
  futureEv?: number | null
) {
  const { g, W, H } = fit(cv);
  const P = 46;
  g.clearRect(0, 0, W, H);
  g.font = "600 16px 'IBM Plex Sans', sans-serif";
  LIFTPTS = [];
  if (!pts.length) {
    g.fillStyle = TC;
    putText(g, W, 'no sets logged for this lift yet', P, H / 2, 'left');
    return;
  }
  const d0 = pts[0].date;
  const todayS = new Date().toISOString().slice(0, 10);
  const d1 = pts[pts.length - 1].date > todayS ? pts[pts.length - 1].date : todayS;
  const t0 = new Date(d0 + 'T12:00:00').getTime();
  const t1 = new Date(d1 + 'T12:00:00').getTime();
  const span = Math.max(1, t1 - t0);
  const px = (dt: string) => P + (W - P - 8) * ((new Date(dt + 'T12:00:00').getTime() - t0) / span);
  let mn = Infinity,
    mx = 0;
  pts.forEach(p => {
    if (p.ev < mn) mn = p.ev;
    if (p.ev > mx) mx = p.ev;
  });
  if (futureEv !== undefined && futureEv !== null) {
    if (futureEv < mn) mn = futureEv;
    if (futureEv > mx) mx = futureEv;
  }
  const pad = (mx - mn) * 0.25 || Math.max(1, mx * 0.05);
  mn = Math.max(0, mn - pad);
  mx += pad;
  const t = niceTicks(mn, mx, 4);
  mn = t.lo;
  mx = t.hi;
  const py = (v: number) => H - P - (H - P - 18) * ((v - mn) / (mx - mn));
  drawYAxis(g, W, H, P, t);
  drawXAxisLabels(g, W, H, P, pts[0].date, pts[pts.length - 1].date);
  const showFuture = futureEv !== undefined && futureEv !== null && pts.length > 0;
  const col = LC[0];
  const linePts = pts.map(p => ({ x: px(p.date), y: py(p.ev) }));
  g.fillStyle = TC;
  putText(g, W, fmtV(pts[0].ev) + ' start', linePts[0].x + 8, py(pts[0].ev) - 12, 'left');
  if (!showFuture)
    putText(
      g,
      W,
      fmtV(pts[pts.length - 1].ev) + ' now',
      W - 8,
      py(pts[pts.length - 1].ev) - 12,
      'right'
    );
  drawLine(g, linePts, col);
  pts.forEach(p => {
    const x = px(p.date),
      y = py(p.ev);
    LIFTPTS.push({ x, y, date: p.date });
    drawPoint(g, x, y, 4, col, false);
  });
  if (futureEv !== undefined && futureEv !== null && pts.length) {
    const fx = Math.min(px(pts[pts.length - 1].date) + 26, W - 14);
    const fy = py(futureEv);
    g.save();
    g.strokeStyle = col;
    g.globalAlpha = 0.85;
    g.setLineDash([4, 3]);
    g.lineWidth = 2;
    g.beginPath();
    g.moveTo(linePts[linePts.length - 1].x, linePts[linePts.length - 1].y);
    g.lineTo(fx, fy);
    g.stroke();
    g.restore();
    g.save();
    g.strokeStyle = col;
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
    g.fillStyle = TC;
    putText(g, W, fmtV(futureEv) + ' next', fx, fy - 10, 'right');
  }
  if (hover !== undefined && hover >= 0 && hover < pts.length) {
    const p = pts[hover];
    const x = px(p.date);
    drawHoverLine(g, H, P, x);
    drawHoverPoint(g, x, py(p.ev), 6, col, false);
  }
}

export function getLiftPts(): Array<{ x: number; y: number; date: string }> {
  return LIFTPTS;
}
