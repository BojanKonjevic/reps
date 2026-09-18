import {
  fit,
  putText,
  LC,
  TC,
  GC,
  STARC,
  trophy,
  drawYAxis,
  drawXAxisLabels,
  drawValueLabels,
  drawHoverLine,
  drawPoint,
  drawHoverPoint,
  drawLine,
  ChartContext,
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

export function liftChart(cv: HTMLCanvasElement, pts: LiftPoint[], ex: string, hover: number) {
  const { g, W, H } = fit(cv);
  const P = 46;
  g.clearRect(0, 0, W, H);
  g.font = '600 12px sans-serif';
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
    if (p.w < mn) mn = p.w;
    if (p.w > mx) mx = p.w;
  });
  const pad = (mx - mn) * 0.25 || Math.max(1, mx * 0.05);
  mn = Math.max(0, mn - pad);
  mx += pad;
  const t = niceTicks(mn, mx, 4);
  mn = t.lo;
  mx = t.hi;
  const py = (v: number) => H - P - (H - P - 18) * ((v - mn) / (mx - mn));
  drawYAxis(g, W, H, P, t);
  drawXAxisLabels(g, W, H, P, pts[0].date, pts[pts.length - 1].date);
  drawValueLabels(g, W, P, py, pts[0].w, pts[pts.length - 1].w, pts[pts.length - 1].pr);
  const col = LC[0];
  const linePts = pts.map(p => ({ x: px(p.date), y: py(p.w) }));
  drawLine(g, linePts, col);
  pts.forEach(p => {
    const x = px(p.date),
      y = py(p.w);
    LIFTPTS.push({ x, y, date: p.date });
    drawPoint(g, x, y, 4, col, p.pr);
  });
  if (hover !== undefined && hover >= 0 && hover < pts.length) {
    const p = pts[hover];
    const x = px(p.date);
    drawHoverLine(g, H, P, x);
    drawHoverPoint(g, x, py(p.w), p.pr ? 10 : 6, col, p.pr);
  }
}

export function getLiftPts(): Array<{ x: number; y: number; date: string }> {
  return LIFTPTS;
}
